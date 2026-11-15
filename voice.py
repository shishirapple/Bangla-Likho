# -*- coding: utf-8 -*-
"""Reliable low-latency voice typing with input health monitoring and recovery."""
import collections
import queue
import threading
import time
import numpy as np

RATE = 16000
BLOCK = 320  # 20 ms; low latency with modest callback overhead


def normalize_pcm16(pcm, target_rms=4200.0, max_gain=5.0):
    """Remove DC offset and gently lift quiet speech without clipping."""
    audio = np.frombuffer(pcm, dtype=np.int16).astype(np.float32)
    if audio.size == 0:
        return pcm
    audio -= float(np.mean(audio))
    rms = float(np.sqrt(np.mean(audio * audio)))
    if rms < 1.0:
        return pcm
    gain = min(max_gain, max(1.0, target_rms / rms))
    peak = float(np.max(np.abs(audio)))
    if peak > 0:
        gain = min(gain, 30000.0 / peak)
    return np.clip(audio * gain, -32768, 32767).astype(np.int16).tobytes()


def denoise_rnnoise_pcm16(pcm, denoiser):
    """Run optional RNNoise on 16 kHz mono PCM via its required 48 kHz API."""
    x = np.frombuffer(pcm, dtype=np.int16)
    if x.size < 160:
        return pcm
    try:
        from scipy.signal import resample_poly
        up = resample_poly(x.astype(np.float32), 3, 1)
    except Exception:
        up = np.interp(
            np.linspace(0, len(x) - 1, len(x) * 3, endpoint=True),
            np.arange(len(x)), x.astype(np.float32)
        )
    up = np.clip(up, -32768, 32767).astype(np.int16)
    padded_len = ((len(up) + 479) // 480) * 480
    if padded_len > len(up):
        up = np.pad(up, (0, padded_len - len(up)))
    chunk = up.reshape(1, -1)
    frames = []
    for item in denoiser.denoise_chunk(chunk, partial=True):
        if not isinstance(item, tuple) or len(item) < 2:
            continue
        frame = np.asarray(item[1], dtype=np.int16).reshape(-1)
        if frame.size:
            frames.append(frame)
    if not frames:
        raise RuntimeError("RNNoise did not return processed audio")
    cleaned = np.concatenate(frames)[:len(up)].astype(np.float32)
    try:
        down = resample_poly(cleaned, 1, 3)
    except Exception:
        usable = (len(cleaned) // 3) * 3
        down = cleaned[:usable].reshape(-1, 3).mean(axis=1)
    down = down[:len(x)]
    if len(down) < len(x):
        down = np.pad(down, (0, len(x) - len(down)))
    return np.clip(down, -32768, 32767).astype(np.int16).tobytes()


def denoise_pcm16(pcm, strength=0.55):
    """Conservative offline spectral gate for steady fan/AC/hum noise.

    It is intentionally conservative: it reduces stationary background noise,
    but cannot separate overlapping speakers or guarantee studio-grade voice
    isolation. Uses NumPy only and never sends audio anywhere.
    """
    if not pcm or strength <= 0:
        return pcm
    x = np.frombuffer(pcm, dtype=np.int16).astype(np.float32)
    if x.size < 1024:
        return pcm
    strength = float(np.clip(strength, 0.0, 0.85))
    frame, hop, nfft = 512, 160, 512
    pad = frame // 2
    padded = np.pad(x, (pad, pad + ((-len(x)) % hop)))
    starts = range(0, len(padded) - frame + 1, hop)
    window = np.hanning(frame).astype(np.float32)
    spectra = []
    for start in starts:
        spectra.append(np.fft.rfft(padded[start:start + frame] * window, n=nfft))
    spec = np.asarray(spectra)
    mag = np.abs(spec)
    frame_energy = np.sqrt(np.mean(mag * mag, axis=1))
    quiet_count = max(1, int(len(mag) * 0.20))
    quiet_idx = np.argsort(frame_energy)[:quiet_count]
    noise = np.median(mag[quiet_idx], axis=0)
    # Spectral subtraction with a soft floor avoids hard musical-noise gating.
    gain = 1.0 - strength * (noise[None, :] / (mag + 1e-6))
    gain = np.clip(gain, 0.22, 1.0)
    # Smooth frequency response to reduce metallic artifacts.
    if gain.shape[1] > 2:
        gain[:, 1:-1] = (gain[:, :-2] + 2.0 * gain[:, 1:-1] + gain[:, 2:]) / 4.0
    cleaned = np.fft.irfft(spec * gain, n=nfft, axis=1)[:, :frame]
    out = np.zeros(len(padded), dtype=np.float32)
    weight = np.zeros(len(padded), dtype=np.float32)
    win2 = window * window
    for i, start in enumerate(starts):
        out[start:start + frame] += cleaned[i] * window
        weight[start:start + frame] += win2
    out /= np.maximum(weight, 1e-4)
    out = out[pad:pad + len(x)]
    peak = float(np.max(np.abs(out))) if out.size else 0.0
    if peak > 32760:
        out *= 32760.0 / peak
    return np.clip(out, -32768, 32767).astype(np.int16).tobytes()


def remove_phrase_overlap(previous_tail, current_text, max_words=5):
    """Remove exact repeated word prefixes caused by overlapping ASR chunks."""
    prev = (previous_tail or "").split()
    curr = (current_text or "").split()
    punctuation = ".,!?;:।॥“”\\\"'()[]{}"
    for size in range(min(max_words, len(prev), len(curr)), 0, -1):
        left = [w.strip(punctuation).casefold() for w in prev[-size:]]
        right = [w.strip(punctuation).casefold() for w in curr[:size]]
        if left == right and all(left):
            return " ".join(curr[size:])
    return current_text


class Segmenter:
    """Adaptive VAD designed to detect normal and quiet speech on laptop mics."""
    def __init__(self, silence_end=0.55, min_speech=0.08, max_len=12.0, preroll=0.38):
        self.silence_blocks = max(1, int(silence_end / (BLOCK / RATE)))
        self.min_blocks = max(1, int(min_speech / (BLOCK / RATE)))
        self.max_blocks = int(max_len / (BLOCK / RATE))
        self.pre = collections.deque(maxlen=max(1, int(preroll / (BLOCK / RATE))))
        self.noise = 35.0
        self.speaking = False
        self.buf, self.silence, self.loud, self.start_len = [], 0, 0, 0

    @staticmethod
    def rms(block):
        x = block.astype(np.float32)
        return float(np.sqrt(np.mean(x * x))) if len(x) else 0.0

    def feed(self, block):
        out = []
        level = self.rms(block)
        # Low fixed floor makes quiet built-in microphones usable. Noise estimate
        # raises the threshold only when the room is genuinely noisy.
        start_threshold = max(35.0, self.noise * 1.9)
        silence_threshold = max(24.0, self.noise * 1.35)
        if not self.speaking:
            # Track ambient noise slowly while idle; do not chase speech peaks.
            if level < max(self.noise * 2.4, 650.0):
                alpha = 0.018 if level > self.noise else 0.055
                self.noise = (1.0 - alpha) * self.noise + alpha * min(level, 2200.0)
            self.pre.append(block.copy())
            self.loud = self.loud + 1 if level > start_threshold else 0
            if self.loud >= 2:
                self.speaking = True
                self.buf = list(self.pre)
                self.start_len = len(self.buf)
                self.silence = 0
        else:
            self.buf.append(block.copy())
            self.silence = self.silence + 1 if level < silence_threshold else 0
            forced_split = len(self.buf) >= self.max_blocks
            if self.silence >= self.silence_blocks or forced_split:
                voiced = len(self.buf) - self.start_len - self.silence + 2
                if voiced >= self.min_blocks:
                    out.append(np.concatenate(self.buf).astype(np.int16).tobytes())
                tail = list(self.buf[-self.pre.maxlen:]) if forced_split else []
                self.speaking, self.buf, self.silence, self.loud = False, [], 0, 0
                self.pre.clear()
                if tail:
                    self.pre.extend(tail)
        return out


class GoogleRec:
    def __init__(self, lang):
        import speech_recognition as sr
        self.sr, self.lang = sr, lang
        self.r = sr.Recognizer()
        self.r.operation_timeout = 10

    def __call__(self, pcm):
        audio = self.sr.AudioData(pcm, RATE, 2)
        try:
            result = self.r.recognize_google(audio, language=self.lang, show_all=True)
            if isinstance(result, dict):
                alternatives = result.get("alternative", [])
                if alternatives:
                    def rank(item):
                        transcript = (item.get("transcript") or "").strip()
                        confidence = float(item.get("confidence", 0.0) or 0.0)
                        words = len(transcript.split())
                        # Prefer confidence; use a small coverage tie-breaker so
                        # an equally confident longer transcript is not discarded.
                        return confidence + min(words, 18) * 0.002
                    best = max(alternatives, key=rank)
                    return (best.get("transcript") or "").strip()
                return ""
            return str(result or "").strip()
        except self.sr.UnknownValueError:
            return ""
        except self.sr.RequestError as exc:
            raise RuntimeError("Speech service/network error: %s" % exc) from exc
        except (OSError, FileNotFoundError) as exc:
            # SpeechRecognition re-encodes the audio with a bundled FLAC tool;
            # if the installation lost it, every request fails this way.
            raise RuntimeError(
                "ভয়েস এনকোডার (FLAC) পাওয়া যায়নি — অ্যাপটি নতুন করে ইনস্টল করুন "
                "(Linux-এ: sudo apt install flac) • %s" % str(exc)[:60]) from exc


class WhisperRec:
    def __init__(self, size, lang):
        from faster_whisper import WhisperModel
        self.model = WhisperModel(size, device="cpu", compute_type="int8")
        self.lang = lang.split("-")[0]

    def __call__(self, pcm):
        audio = np.frombuffer(pcm, dtype=np.int16).astype(np.float32) / 32768.0
        segments, _ = self.model.transcribe(
            audio, language=self.lang, vad_filter=False, beam_size=5,
            best_of=5, temperature=0.0, condition_on_previous_text=False,
            initial_prompt="বাংলা কথোপকথন। বাংলাদেশের প্রচলিত বাংলা, আঞ্চলিক শব্দ, সাধু ও চলিত ভাষা।"
        )
        return " ".join(s.text.strip() for s in segments).strip()


def make_recognizer(cfg):
    lang = cfg.get("voice_lang", "bn-BD")
    if cfg.get("voice_engine", "google") == "whisper":
        return WhisperRec(cfg.get("whisper_model", "tiny"), lang)
    return GoogleRec(lang)


class VoiceTyper:
    """Callbacks: ui.voice(bool), ui.status(str)."""
    def __init__(self, cfg, out, ui, recognizer=None):
        self.cfg, self.out, self.ui = cfg, out, ui
        self.rec = recognizer
        self.listening = False
        self.starting = False
        self._start_generation = 0
        self.stream = None
        # Unbounded queues prevent routine ASR latency from silently dropping
        # audio blocks or complete recognized phrases. VAD is lightweight.
        self.q = queue.Queue()
        self.seg_q = queue.Queue()
        self.fails = 0
        self._threads = []
        self._lock = threading.RLock()
        self._last_callback = 0.0
        self._last_audio = 0.0
        self._last_level = 0.0
        self._callback_count = 0
        self._last_health_notice = 0.0
        self._recoveries = 0
        self._recovering = False
        self._device_name = "Default microphone"
        self._last_text_tail = ""
        self._rnnoise = None
        self._rnnoise_unavailable = False

    def toggle(self):
        (self.stop if (self.listening or self.starting) else self.start)()

    @staticmethod
    def _clear_queue(q):
        while True:
            try:
                q.get_nowait()
            except queue.Empty:
                return

    def _get_rnnoise(self):
        if self._rnnoise is not None:
            return self._rnnoise
        if self._rnnoise_unavailable:
            raise RuntimeError("RNNoise package নেই • pip install pyrnnoise")
        try:
            from pyrnnoise import RNNoise
            self._rnnoise = RNNoise(sample_rate=48000)
            return self._rnnoise
        except Exception as exc:
            self._rnnoise_unavailable = True
            raise RuntimeError("RNNoise চালু হয়নি: %s • pip install pyrnnoise" % str(exc)[:70]) from exc

    def _status(self, message):
        try:
            self.ui.status.emit(message)
        except Exception:
            pass

    def _voice_state(self, enabled):
        try:
            self.ui.voice.emit(enabled)
        except Exception:
            pass

    def _open_stream(self):
        import sounddevice as sd
        device = self.cfg.get("mic_device")
        try:
            info = sd.query_devices(device, "input")
            self._device_name = info.get("name", "Microphone")
            if int(info.get("max_input_channels", 0)) < 1:
                raise RuntimeError("Selected device has no input channels")
        except Exception:
            if device is not None:
                raise
            info = sd.query_devices(kind="input")
            self._device_name = info.get("name", "Default microphone")
        stream = sd.InputStream(
            samplerate=RATE, channels=1, dtype="int16", blocksize=BLOCK,
            device=device, callback=self._audio_cb, latency="low"
        )
        stream.start()
        return stream

    def start(self):
        """Return immediately; microphone/recognizer initialization runs off the UI thread."""
        with self._lock:
            if self.listening or self.starting:
                return
            self.starting = True
            self._start_generation += 1
            generation = self._start_generation
        self._status("মাইক্রোফোন চালু হচ্ছে…")
        worker = threading.Thread(target=self._start_worker, args=(generation,),
                                  daemon=True, name="BanglaType-VoiceStart")
        worker.start()

    def _start_worker(self, generation):
        stream = None
        try:
            if self.rec is None:
                recognizer = make_recognizer(self.cfg)
            else:
                recognizer = self.rec
            stream = self._open_stream()
            with self._lock:
                if not self.starting or generation != self._start_generation:
                    stream.stop()
                    stream.close()
                    return
                self.rec = recognizer
                self._clear_queue(self.q)
                self._clear_queue(self.seg_q)
                self.seg = Segmenter(max(0.50, float(self.cfg.get("voice_silence", 0.55))))
                self._last_callback = time.monotonic()
                self._last_audio = 0.0
                self._last_level = 0.0
                self._callback_count = 0
                self._recoveries = 0
                self._recovering = False
                self._last_text_tail = ""
                self.listening = True
                self.starting = False
                self.stream = stream
                stream = None
            self._threads = [
                threading.Thread(target=self._vad_loop, daemon=True, name="BanglaType-VAD"),
                threading.Thread(target=self._rec_loop, daemon=True, name="BanglaType-ASR"),
                threading.Thread(target=self._health_loop, daemon=True, name="BanglaType-AudioHealth"),
            ]
            for thread in self._threads:
                thread.start()
            self._voice_state(True)
            self._status("Mic: %s • স্বাভাবিকভাবে কথা বলুন" % self._device_name)
        except Exception as exc:
            if stream:
                try:
                    stream.stop()
                    stream.close()
                except Exception:
                    pass
            with self._lock:
                is_current = generation == self._start_generation
                if is_current:
                    self.starting = False
                    self.listening = False
                    self.stream = None
            if is_current:
                self._voice_state(False)
                self._status("মাইক্রোফোন চালু হয়নি: %s" % str(exc)[:110])

    def _put_stop(self, q):
        try:
            q.put_nowait(None)
        except queue.Full:
            try:
                q.get_nowait()
            except queue.Empty:
                pass
            try:
                q.put_nowait(None)
            except queue.Full:
                pass

    def stop(self):
        with self._lock:
            if self.starting and not self.listening:
                self.starting = False
                self._start_generation += 1
                self._voice_state(False)
                self._status("Voice start বাতিল")
                return
            if not self.listening and self.stream is None:
                self._voice_state(False)
                return
            self.listening = False
            self.starting = False
            self._start_generation += 1
            stream, self.stream = self.stream, None
        self._put_stop(self.q)
        self._put_stop(self.seg_q)
        self._voice_state(False)
        self._status("Voice বন্ধ")

        def release_audio():
            try:
                if stream:
                    stream.stop()
                    stream.close()
            except Exception:
                pass
        threading.Thread(target=release_audio, daemon=True, name="BanglaType-VoiceStop").start()

    def _audio_cb(self, indata, frames, timing, status):
        if not self.listening:
            return
        now = time.monotonic()
        block = indata[:, 0].copy()
        level = Segmenter.rms(block)
        self._last_callback = now
        self._callback_count += 1
        self._last_level = level
        if level >= 12:
            self._last_audio = now
        if status:
            self._status("মাইক্রোফোন সতর্কতা: %s" % str(status)[:70])
        # Queue is intentionally unbounded: never discard a captured audio block
        # merely because the recognizer is temporarily slower than real time.
        self.q.put_nowait(block)

    def _vad_loop(self):
        while self.listening:
            try:
                block = self.q.get(timeout=0.25)
            except queue.Empty:
                continue
            if block is None:
                break
            for phrase in self.seg.feed(block):
                # Keep every completed phrase queued until ASR can process it.
                self.seg_q.put_nowait(phrase)

    def _health_loop(self):
        """Distinguish live microphone, quiet input and a stalled PortAudio stream."""
        while self.listening:
            time.sleep(1.0)
            if not self.listening:
                break
            now = time.monotonic()
            last_cb = self._last_callback
            if now - last_cb > 2.2:
                self._status("মাইক্রোফোন ইনপুট থেমে গেছে • পুনরায় সংযোগের চেষ্টা চলছে")
                self._recover_stream()
                continue
            if self.q.qsize() > 500 or self.seg_q.qsize() > 12:
                self._status("Voice processing backlog • একটু অপেক্ষা করুন, অডিও সংরক্ষিত আছে")
            no_recent_audio = (not self._last_audio) or (now - self._last_audio > 7.0)
            if self._callback_count > 100 and no_recent_audio:
                if now - self._last_health_notice > 7.0:
                    self._last_health_notice = now
                    self._status("Mic connected, কিন্তু input level খুব কম/নেই • Microphone পরীক্ষা করুন")
            elif self._callback_count:
                self._status("মাইক্রোফোন সক্রিয় • কথা বলুন")

    def _recover_stream(self):
        with self._lock:
            if not self.listening or self._recovering:
                return
            self._recovering = True
            old, self.stream = self.stream, None
        try:
            if old:
                try:
                    old.stop()
                    old.close()
                except Exception:
                    pass
            time.sleep(0.15)
            if self.listening:
                new_stream = self._open_stream()
                with self._lock:
                    if self.listening:
                        self.stream = new_stream
                        self._last_callback = time.monotonic()
                        self._recoveries += 1
                        self._status("মাইক্রোফোন পুনরায় সংযুক্ত • আবার বলুন")
                    else:
                        new_stream.stop()
                        new_stream.close()
        except Exception as exc:
            self._status("মাইক্রোফোন পুনরায় চালু হয়নি: %s" % str(exc)[:90])
            self._recoveries += 1
            if self._recoveries >= 3:
                self._status("Voice বন্ধ করা হয়েছে • Settings থেকে Microphone নির্বাচন করুন")
                self.stop()
        finally:
            self._recovering = False

    def _rec_loop(self):
        while self.listening:
            try:
                phrase = self.seg_q.get(timeout=0.25)
            except queue.Empty:
                continue
            if phrase is None:
                break
            try:
                self._status("কথা শনাক্ত করা হচ্ছে…")
                noise_mode = self.cfg.get("voice_noise_suppression", "medium")
                if noise_mode == "neural":
                    try:
                        cleaned = denoise_rnnoise_pcm16(phrase, self._get_rnnoise())
                    except Exception as noise_exc:
                        self._status(str(noise_exc)[:110] + " • Medium mode ব্যবহার হচ্ছে")
                        cleaned = denoise_pcm16(phrase, strength=0.55)
                else:
                    strength = {"off": 0.0, "light": 0.30, "medium": 0.55, "strong": 0.72}.get(noise_mode, 0.55)
                    cleaned = denoise_pcm16(phrase, strength=strength)
                recognized = self.rec(normalize_pcm16(cleaned)).strip()
                recognized = remove_phrase_overlap(self._last_text_tail, recognized).strip()
                self.fails = 0
                if recognized and self.listening:
                    self._last_text_tail = " ".join(recognized.split()[-5:])
                    self.out.text(recognized + " ")
                    self._status("মাইক্রোফোন সক্রিয় • কথা বলুন")
                elif self.listening:
                    self._status("শব্দ পাওয়া গেছে, বাক্য বোঝা যায়নি • আবার বলুন")
            except Exception as exc:
                self.fails += 1
                self._status("Voice service সমস্যা: %s" % str(exc)[:90])
                if self.fails >= 5:
                    self._status("Voice বন্ধ • ইন্টারনেট বা Speech Settings পরীক্ষা করুন")
                    self.stop()
                    break
