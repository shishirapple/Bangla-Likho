import os
import sys
import unittest
import time
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from voice import normalize_pcm16, denoise_pcm16, denoise_rnnoise_pcm16, remove_phrase_overlap, Segmenter, BLOCK, VoiceTyper


class Signal:
    def __init__(self): self.items=[]
    def emit(self, value): self.items.append(value)


class FakeUI:
    def __init__(self):
        self.voice=Signal()
        self.status=Signal()


class FakeOutput:
    def text(self, value): pass


class FakeStream:
    def __init__(self):
        self.closed=False
    def stop(self): pass
    def close(self): self.closed=True


class VoiceTests(unittest.TestCase):
    def test_normalizer_boosts_quiet_pcm_without_clipping(self):
        source = (np.sin(np.linspace(0, 20, 16000)) * 250).astype(np.int16)
        result = normalize_pcm16(source.tobytes())
        decoded = np.frombuffer(result, dtype=np.int16)
        self.assertEqual(decoded.size, source.size)
        self.assertGreater(np.sqrt(np.mean(decoded.astype(float) ** 2)), 500)
        self.assertLessEqual(np.max(np.abs(decoded.astype(np.int32))), 32768)

    def test_normalizer_preserves_silence(self):
        silence = np.zeros(100, dtype=np.int16).tobytes()
        self.assertEqual(normalize_pcm16(b""), b"")
        self.assertEqual(normalize_pcm16(silence), silence)

    def test_rnnoise_adapter_preserves_16khz_pcm_duration(self):
        class FakeRNNoise:
            def denoise_chunk(self, chunk, partial=False):
                self.shape = chunk.shape
                for start in range(0, chunk.shape[1], 480):
                    frame = chunk[:, start:start + 480]
                    if frame.shape[1] < 480:
                        frame = np.pad(frame, ((0, 0), (0, 480 - frame.shape[1])))
                    yield np.array([0.9]), frame
        fake = FakeRNNoise()
        pcm = (np.sin(np.linspace(0, 30, 1600)) * 1200).astype(np.int16).tobytes()
        out = denoise_rnnoise_pcm16(pcm, fake)
        self.assertEqual(len(out), len(pcm))
        self.assertEqual(fake.shape[0], 1)
        self.assertGreater(len(out), 0)

    def test_noise_suppression_preserves_duration_and_nonzero_voice(self):
        t = np.arange(8000, dtype=np.float32) / 16000.0
        speech = 900 * np.sin(2 * np.pi * 180 * t)
        noise = 180 * np.sin(2 * np.pi * 60 * t) + 90 * np.random.default_rng(7).normal(size=t.size)
        mixed = np.clip(speech + noise, -32768, 32767).astype(np.int16).tobytes()
        cleaned = denoise_pcm16(mixed, strength=0.55)
        out = np.frombuffer(cleaned, dtype=np.int16)
        self.assertEqual(out.size, 8000)
        self.assertGreater(np.sqrt(np.mean(out.astype(np.float32) ** 2)), 100.0)
        self.assertLess(np.sqrt(np.mean(out.astype(np.float32) ** 2)),
                        np.sqrt(np.mean(np.frombuffer(mixed, dtype=np.int16).astype(np.float32) ** 2)))
        self.assertGreater(np.corrcoef(out.astype(np.float32), speech)[0, 1], 0.80)
        self.assertEqual(denoise_pcm16(mixed, strength=0), mixed)

    def test_overlapping_voice_chunks_do_not_repeat_words(self):
        self.assertEqual(
            remove_phrase_overlap("আমি আজকে বাজারে যাচ্ছি", "বাজারে যাচ্ছি এবং ফিরব"),
            "এবং ফিরব"
        )
        self.assertEqual(
            remove_phrase_overlap("hello there", "there friend"),
            "friend"
        )

    def test_vad_detects_quiet_speech(self):
        seg = Segmenter(silence_end=0.10, min_speech=0.06, max_len=2, preroll=0.06)
        quiet = np.zeros(BLOCK, dtype=np.int16)
        # Low but audible speech-level signal, approximately 70 RMS.
        t = np.arange(BLOCK, dtype=np.float32)
        speech = (np.sin(2 * np.pi * 440 * t / 16000) * 100).astype(np.int16)
        output = []
        for _ in range(5):
            output.extend(seg.feed(quiet))
        for _ in range(16):
            output.extend(seg.feed(speech))
        for _ in range(9):
            output.extend(seg.feed(quiet))
        self.assertTrue(output, "VAD should emit a quiet spoken segment")

    def test_vad_normal_speech(self):
        seg = Segmenter(silence_end=0.10, min_speech=0.06, max_len=2, preroll=0.06)
        quiet = np.zeros(BLOCK, dtype=np.int16)
        speech = np.full(BLOCK, 900, dtype=np.int16)
        output = []
        for _ in range(15):
            output.extend(seg.feed(speech))
        for _ in range(9):
            output.extend(seg.feed(quiet))
        self.assertTrue(output)


    def test_voice_queues_are_non_evicting(self):
        voice = VoiceTyper({}, FakeOutput(), FakeUI(), recognizer=lambda pcm: "")
        self.assertEqual(voice.q.maxsize, 0)
        self.assertEqual(voice.seg_q.maxsize, 0)

    def test_voice_start_does_not_block_caller(self):
        ui = FakeUI()
        voice = VoiceTyper({}, FakeOutput(), ui, recognizer=lambda pcm: "")
        stream = FakeStream()
        def slow_open():
            time.sleep(0.15)
            return stream
        voice._open_stream = slow_open
        started = time.perf_counter()
        voice.start()
        elapsed = time.perf_counter() - started
        self.assertLess(elapsed, 0.08)
        deadline = time.time() + 1.5
        while not voice.listening and time.time() < deadline:
            time.sleep(0.01)
        self.assertTrue(voice.listening)
        voice.stop()
        deadline = time.time() + 1.0
        while not stream.closed and time.time() < deadline:
            time.sleep(0.01)
        self.assertTrue(stream.closed)

    def test_cancelled_voice_start_releases_late_stream(self):
        ui = FakeUI()
        voice = VoiceTyper({}, FakeOutput(), ui, recognizer=lambda pcm: "")
        stream = FakeStream()
        def slow_open():
            time.sleep(0.12)
            return stream
        voice._open_stream = slow_open
        voice.start()
        voice.stop()
        deadline = time.time() + 1.0
        while not stream.closed and time.time() < deadline:
            time.sleep(0.01)
        self.assertFalse(voice.listening)
        self.assertTrue(stream.closed)


class FlacEncoderTests(unittest.TestCase):
    """Google speech needs FLAC; we must encode it without an external tool."""

    def test_flac_data_has_a_flac_header(self):
        import speech_recognition as sr

        from voice import install_flac_encoder

        self.assertTrue(install_flac_encoder(sr))
        audio = sr.AudioData(b"\x00\x00" * 1600, 16000, 2)
        data = audio.get_flac_data(convert_rate=16000, convert_width=2)
        self.assertEqual(data[:4], b"fLaC")
        self.assertGreater(len(data), 40)

    def test_install_is_idempotent(self):
        import speech_recognition as sr

        from voice import install_flac_encoder

        self.assertTrue(install_flac_encoder(sr))
        self.assertTrue(install_flac_encoder(sr))


if __name__ == "__main__":
    unittest.main()
