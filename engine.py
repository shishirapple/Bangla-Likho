# -*- coding: utf-8 -*-
"""Bangla Likho engine: Avro-style rules + dictionary-driven (phonetic-folded) suggestions."""
import bisect
import hashlib
import json
import marshal
import math
import os
import platform
import shutil
import re
import threading
import traceback
import unicodedata
from collections import defaultdict

APP = "Bangla Likho"
IS_WIN = platform.system() == "Windows"
_DPAPI_PREFIX = b"BLDPAPI1:"


def _dpapi_transform(data: bytes, protect: bool) -> bytes:
    """Protect/unprotect local JSON with Windows user-scope DPAPI."""
    if not IS_WIN:
        raise RuntimeError("Windows DPAPI is only available on Windows")
    import ctypes
    from ctypes import wintypes

    class DATA_BLOB(ctypes.Structure):
        _fields_ = [("cbData", wintypes.DWORD), ("pbData", ctypes.POINTER(ctypes.c_ubyte))]

    source = ctypes.create_string_buffer(data)
    in_blob = DATA_BLOB(len(data), ctypes.cast(source, ctypes.POINTER(ctypes.c_ubyte)))
    out_blob = DATA_BLOB()
    crypt32 = ctypes.WinDLL("crypt32", use_last_error=True)
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    if protect:
        fn = crypt32.CryptProtectData
        fn.argtypes = [ctypes.POINTER(DATA_BLOB), wintypes.LPCWSTR, ctypes.POINTER(DATA_BLOB),
                       ctypes.c_void_p, ctypes.c_void_p, wintypes.DWORD, ctypes.POINTER(DATA_BLOB)]
        fn.restype = wintypes.BOOL
        ok = fn(ctypes.byref(in_blob), "Bangla Likho local data", None, None, None, 0, ctypes.byref(out_blob))
    else:
        fn = crypt32.CryptUnprotectData
        fn.argtypes = [ctypes.POINTER(DATA_BLOB), ctypes.POINTER(wintypes.LPWSTR),
                       ctypes.POINTER(DATA_BLOB), ctypes.c_void_p, ctypes.c_void_p,
                       wintypes.DWORD, ctypes.POINTER(DATA_BLOB)]
        fn.restype = wintypes.BOOL
        ok = fn(ctypes.byref(in_blob), None, None, None, None, 0, ctypes.byref(out_blob))
    if not ok:
        raise ctypes.WinError(ctypes.get_last_error())
    try:
        return ctypes.string_at(out_blob.pbData, out_blob.cbData)
    finally:
        kernel32.LocalFree.argtypes = [ctypes.c_void_p]
        kernel32.LocalFree.restype = ctypes.c_void_p
        kernel32.LocalFree(ctypes.cast(out_blob.pbData, ctypes.c_void_p))


def config_dir():
    # Explicit override (portable installs, tests, sandboxed runs).
    override = os.environ.get("BANGLA_LIKHO_HOME")
    if override:
        return os.path.abspath(override)
    if IS_WIN:
        base = os.environ.get("APPDATA", os.path.expanduser("~"))
    else:
        base = os.environ.get("XDG_CONFIG_HOME", os.path.expanduser("~/.config"))
    d = os.path.join(base, APP)
    legacy = os.path.join(base, "BanglaType")
    # One-time migration keeps learned words and settings after the rename.
    if not os.path.exists(d) and os.path.isdir(legacy):
        try:
            shutil.copytree(legacy, d)
        except Exception:
            pass
    os.makedirs(d, mode=0o700, exist_ok=True)
    if not IS_WIN:
        try:
            os.chmod(d, 0o700)
        except OSError:
            pass
    return d


def load_json(path, default):
    try:
        with open(path, "rb") as f:
            payload = f.read()
        encrypted = payload.startswith(_DPAPI_PREFIX)
        if encrypted:
            payload = _dpapi_transform(payload[len(_DPAPI_PREFIX):], protect=False)
        obj = json.loads(payload.decode("utf-8"))
        # Migrate older plaintext local JSON files to Windows user-scope DPAPI.
        if IS_WIN and not encrypted:
            save_json(path, obj)
        return obj
    except Exception:
        return default


def save_json(path, obj):
    """Atomically save local JSON; DPAPI on Windows, owner-only POSIX permissions elsewhere."""
    tmp = path + ".tmp"
    try:
        os.makedirs(os.path.dirname(path) or ".", mode=0o700, exist_ok=True)
        payload = json.dumps(obj, ensure_ascii=False, indent=2).encode("utf-8")
        if IS_WIN:
            payload = _DPAPI_PREFIX + _dpapi_transform(payload, protect=True)
        flags = os.O_WRONLY | os.O_CREAT | os.O_TRUNC
        fd = os.open(tmp, flags, 0o600)
        with os.fdopen(fd, "wb") as f:
            f.write(payload)
            f.flush()
            os.fsync(f.fileno())
        if not IS_WIN:
            try:
                os.chmod(tmp, 0o600)
            except OSError:
                pass
        os.replace(tmp, path)
    except Exception:
        try:
            if os.path.exists(tmp):
                os.remove(tmp)
        except OSError:
            pass
        traceback.print_exc()

# ---------------------------------------------------------------- rules
HAS = "\u09cd"  # hasanta
YA = "\u09df"  # য়
RRA = "\u09dc"  # ড়
RHA = "\u09dd"  # ঢ়

CONS = {
    "kkh": "ক" + HAS + "ষ", "ngg": "ঙ" + HAS + "গ", "gg": "জ" + HAS + "ঞ",
    "chh": "ছ", "ch": "চ", "kh": "খ", "gh": "ঘ", "jh": "ঝ", "Th": "ঠ", "Dh": "ঢ",
    "th": "থ", "dh": "ধ", "ph": "ফ", "bh": "ভ", "sh": "শ", "Sh": "ষ",
    "Rh": RHA, "Ng": "ঙ", "NG": "ঙ",
    "k": "ক", "g": "গ", "c": "চ", "j": "জ", "T": "ট", "D": "ড", "N": "ণ",
    "t": "ত", "d": "দ", "n": "ন", "p": "প", "f": "ফ", "b": "ব", "v": "ভ",
    "m": "ম", "z": "য", "r": "র", "l": "ল", "S": "শ", "s": "স", "h": "হ",
    "R": RRA, "Y": YA, "q": "ক", "x": "ক" + HAS + "স",
}
VOW = {
    "oi": ("ঐ", "ৈ"), "ou": ("ঔ", "ৌ"), "aa": ("আ", "া"), "ii": ("ঈ", "ী"),
    "uu": ("ঊ", "ূ"), "rri": ("ঋ", "ৃ"),
    "a": ("আ", "া"), "A": ("অ" + HAS + "য" + "া", HAS + "য" + "া"),
    "i": ("ই", "ি"), "I": ("ঈ", "ী"), "u": ("উ", "ু"), "U": ("ঊ", "ূ"),
    "e": ("এ", "ে"), "O": ("ও", "ো"),
}
SPECIAL = {"o", "w", "y", "ng", "^"}
TOKENS = set(CONS) | set(VOW) | SPECIAL

# conjuncts we join automatically (first letter -> allowed second letters)
_PAIRS = {
    "ক": "টতনমরলযস", "খ": "য", "গ": "গধনমলরয", "ঘ": "নরয", "চ": "চছয",
    "জ": "জঝয", "ঞ": "চজছ", "ট": "টরয", "ড": "ডরয", "ণ": "টঠডণময",
    "ত": "তথনময র".replace(" ", ""), "থ": "য", "দ": "দধনময রভ".replace(" ", ""),
    "ধ": "যরন", "ন": "টঠডতথদধনমযসফ", "প": "তপযরলস", "ফ": "রলয",
    "ব": "জদধবযরল", "ভ": "যরল", "ম": "নপফবভময ল".replace(" ", ""),
    "ল": "কগটডপফমলয", "শ": "চনময রলছ".replace(" ", ""), "ষ": "কটঠণপফময",
    "স": "কখটতথনপফমযরল", "হ": "নময রল".replace(" ", ""), "য": "য",
}
PAIRS = {(a, b) for a, s in _PAIRS.items() for b in s}
RO_OK = set("কগঘটডতথদধপফবভশসহ")  # these + র => ক্র, গ্র, প্র ...


def _joinable(a, b, mode):
    if mode == "avro":
        return True
    if a == "র":
        return mode != "noreph"
    if b == "য":
        return True
    if b == "র" and a in RO_OK:
        return True
    return (a, b) in PAIRS


def tokenize(raw):
    toks, i, n = [], 0, len(raw)
    while i < n:
        for L in (3, 2, 1):
            s = raw[i:i + L]
            if len(s) == L and s in TOKENS:
                toks.append(s)
                i += L
                break
        else:
            toks.append(raw[i])
            i += 1
    return toks


def _convert(raw, mode="smart"):
    toks = tokenize(raw)
    out = []
    st = {"prev": "S", "last": "", "joined": False}  # prev: S start, C cons, V vowel, I inherent, M mark, O other

    def cons(val, base):
        if st["prev"] == "C" and _joinable(st["last"], base, mode):
            out.append(HAS)
            st["joined"] = True
        else:
            st["joined"] = False
        out.append(val)
        st["prev"] = "C"
        st["last"] = base

    for k, t in enumerate(toks):
        is_last = k == len(toks) - 1
        if t == "ng":
            nxt = toks[k + 1][0] if k + 1 < len(toks) else ""
            if nxt and nxt in "aeiouAEIOU":
                cons("ঙ", "ঙ")
            else:
                out.append("ং")
                st["prev"], st["joined"] = "M", False
        elif t in CONS:
            v = CONS[t]
            cons(v, v[-1])
        elif t == "y":
            if st["prev"] == "C":
                cons("য", "য")
            else:
                cons(YA, YA)
        elif t == "w":
            if st["prev"] == "C":
                out.append(HAS + "ব")
                st["prev"], st["last"], st["joined"] = "C", "ব", True
            else:
                out.append("ও")
                st["prev"], st["joined"] = "V", False
        elif t == "^":
            out.append("ঁ")
            st["prev"], st["joined"] = "M", False
        elif t == "o":
            if st["prev"] == "C":
                if is_last and mode != "avro" and not st["joined"]:
                    out.append("ো")
                    st["prev"] = "V"
                else:
                    st["prev"] = "I"
            elif st["prev"] == "S":
                out.append("অ")
                st["prev"] = "V"
            else:
                out.append("ও")
                st["prev"] = "V"
            st["joined"] = False
        elif t in VOW:
            ind, kar = VOW[t]
            out.append(kar if st["prev"] == "C" else ind)
            st["prev"], st["joined"] = "V", False
        else:
            out.append(t)
            st["prev"], st["joined"] = "O", False
    return "".join(out)



def convert(raw, mode="smart"):
    """mode: smart (default) | noreph | avro   -> NFC-normalised Bangla"""
    return unicodedata.normalize("NFC", _convert(raw, mode))


ALT = {
    "o": ["O"], "O": ["o"], "i": ["I"], "I": ["i"], "u": ["U"], "U": ["u"],
    "s": ["sh", "S"], "sh": ["s", "Sh"], "S": ["s"], "Sh": ["sh"],
    "ch": ["chh"], "chh": ["ch"],
    "t": ["T", "th"], "T": ["t"], "th": ["t", "Th"], "Th": ["th"],
    "d": ["D", "dh"], "D": ["d"], "dh": ["d", "Dh"], "Dh": ["dh"],
    "n": ["N"], "N": ["n"], "z": ["j"], "j": ["z"], "r": ["R"], "R": ["r"],
    "a": ["A"], "A": ["a"],
}


def variants(raw):
    toks = tokenize(raw)
    for idx in range(len(toks) - 1, -1, -1):
        for a in ALT.get(toks[idx], []):
            yield "".join(toks[:idx] + [a] + toks[idx + 1:])


SEED = {
    # greetings / common
    "assalamualaikum": "আসসালামু আলাইকুম", "walaikumassalam": "ওয়ালাইকুম আসসালাম",
    "salam": "সালাম", "dhonnobad": "ধন্যবাদ", "dhonyobad": "ধন্যবাদ",
    "sir": "স্যার", "sar": "স্যার", "madam": "ম্যাডাম", "mam": "ম্যাম",
    "ji": "জি", "jii": "জি", "hya": "হ্যাঁ", "ha": "হ্যাঁ", "hmm": "হুম",
    "na": "না", "nai": "নেই", "ache": "আছে", "achi": "আছি", "achen": "আছেন", "acho": "আছো",
    "ami": "আমি", "amar": "আমার", "amake": "আমাকে", "amader": "আমাদের", "amra": "আমরা",
    "apni": "আপনি", "apnar": "আপনার", "apnake": "আপনাকে", "apnader": "আপনাদের", "apnara": "আপনারা",
    "tumi": "তুমি", "tomar": "তোমার", "tomake": "তোমাকে", "tomra": "তোমরা",
    "tara": "তারা", "tader": "তাদের", "se": "সে", "ei": "এই", "oi": "ওই",
    "eta": "এটা", "ota": "ওটা", "kono": "কোনো", "kichu": "কিছু", "kintu": "কিন্তু",
    "ebong": "এবং", "ar": "আর", "ba": "বা", "tai": "তাই", "tahole": "তাহলে", "jodi": "যদি",
    "karon": "কারণ", "keno": "কেন", "kemon": "কেমন", "kothay": "কোথায়", "kokhon": "কখন",
    "kobe": "কবে", "koto": "কত", "ke": "কে",
    "bhalo": "ভালো", "kharap": "খারাপ", "thik": "ঠিক", "thikache": "ঠিক আছে",
    "thikana": "ঠিকানা", "thikanay": "ঠিকানায়",
    # verbs that Avro-style rules get wrong
    "lagbe": "লাগবে", "korte": "করতে", "korbo": "করব", "korbe": "করবে", "korben": "করবেন",
    "korchi": "করছি", "korchen": "করছেন", "korechi": "করেছি", "korechen": "করেছেন",
    "dorkar": "দরকার", "bolchi": "বলছি", "bolchen": "বলছেন", "bolbo": "বলব",
    "bolben": "বলবেন", "bolte": "বলতে", "dibo": "দিব", "dibe": "দিবে", "diben": "দিবেন",
    "dilam": "দিলাম", "nilam": "নিলাম", "niben": "নিবেন", "nibo": "নিব", "pabo": "পাব",
    "paben": "পাবেন", "pathabo": "পাঠাব", "pathaben": "পাঠাবেন", "pathan": "পাঠান",
    "pathiye": "পাঠিয়ে", "kinben": "কিনবেন", "kinbo": "কিনব", "kinte": "কিনতে",
    "jabo": "যাব", "jaben": "যাবেন", "asben": "আসবেন", "asbo": "আসব",
    "dekhben": "দেখবেন", "dekhbo": "দেখব", "hoyeche": "হয়েছে",
    # time
    "sob": "সব", "shob": "সব", "somoy": "সময়", "ekhon": "এখন", "pore": "পরে", "age": "আগে",
    "aj": "আজ", "kal": "কাল", "porshu": "পরশু", "sokal": "সকাল", "dupur": "দুপুর",
    "bikal": "বিকাল", "sondha": "সন্ধ্যা", "rat": "রাত", "din": "দিন",
    # sales / telecom words
    "taka": "টাকা", "tk": "টাকা", "dam": "দাম", "mullo": "মূল্য", "bkash": "বিকাশ",
    "nagad": "নগদ", "rocket": "রকেট", "offer": "অফার", "discount": "ডিসকাউন্ট",
    "price": "প্রাইস", "product": "প্রোডাক্ট", "order": "অর্ডার", "delivery": "ডেলিভারি",
    "mobile": "মোবাইল", "number": "নাম্বার", "nambar": "নাম্বার", "call": "কল",
    "customer": "কাস্টমার", "service": "সার্ভিস", "payment": "পেমেন্ট", "cash": "ক্যাশ",
    "online": "অনলাইন", "package": "প্যাকেজ", "plan": "প্ল্যান", "internet": "ইন্টারনেট",
    "connection": "কানেকশন", "bill": "বিল", "recharge": "রিচার্জ", "sim": "সিম",
    "whatsapp": "হোয়াটসঅ্যাপ", "facebook": "ফেসবুক", "messenger": "মেসেঞ্জার",
    "email": "ইমেইল", "address": "অ্যাড্রেস", "confirm": "কনফার্ম", "cancel": "ক্যানসেল",
    "sorry": "সরি", "please": "প্লিজ", "thanks": "থ্যাংকস", "ok": "ওকে",
    "shuvo": "শুভ", "shubho": "শুভ", "shagotom": "স্বাগতম", "allah": "আল্লাহ", "hafez": "হাফেজ",
    # places
    "dhaka": "ঢাকা", "rajshahi": "রাজশাহী", "chattogram": "চট্টগ্রাম", "sylhet": "সিলেট",
    "barishal": "বরিশাল", "rangpur": "রংপুর", "mymensingh": "ময়মনসিংহ", "bogura": "বগুড়া",
}





# Curated high-confidence Banglish aliases. These are intentionally local:
# typed words are never uploaded to a remote service for prediction.
ALIASES = {
    # High-confidence Bengali orthography: common Banglish spellings and typos.
    # Common English loanwords: preserve standard Bengali spelling.
    "test": "টেস্ট", "tests": "টেস্ট", "tested": "টেস্টেড",
    "testing": "টেস্টিং", "tester": "টেস্টার",
    "perform": "পারফর্ম", "performs": "পারফর্ম",
    "performed": "পারফর্মড", "performing": "পারফর্মিং",
    "performance": "পারফরম্যান্স", "performer": "পারফর্মার",
    "best": "বেস্ট", "first": "ফার্স্ট", "fast": "ফাস্ট",
    "smart": "স্মার্ট", "smooth": "স্মুথ", "speed": "স্পিড",
    "accurate": "অ্যাকুরেট", "accuracy": "অ্যাকুরেসি",
    "keyboard": "কিবোর্ড", "keyboards": "কিবোর্ড",
    "software": "সফটওয়্যার", "hardware": "হার্ডওয়্যার",
    "update": "আপডেট", "version": "ভার্সন",
    "system": "সিস্টেম", "settings": "সেটিংস",
    "option": "অপশন", "options": "অপশন",
    "screen": "স্ক্রিন", "window": "উইন্ডো",
    "voice": "ভয়েস", "typing": "টাইপিং",
    "instant": "ইনস্ট্যান্ট", "response": "রেসপন্স",
    "latency": "লেটেন্সি", "internet": "ইন্টারনেট",
    "offline": "অফলাইন", "online": "অনলাইন",
    "attobisshar": "আত্মবিশ্বাস", "atmobisshar": "আত্মবিশ্বাস",
    "attobisshas": "আত্মবিশ্বাস", "atmobisshas": "আত্মবিশ্বাস",
    "attobishshar": "আত্মবিশ্বাস", "atmobishshar": "আত্মবিশ্বাস",
    "attobishshas": "আত্মবিশ্বাস", "atmobishshas": "আত্মবিশ্বাস",
    "attobishash": "আত্মবিশ্বাস", "atmobishash": "আত্মবিশ্বাস",
    "babohar": "ব্যবহার", "byabohar": "ব্যবহার", "bebohar": "ব্যবহার",
    "babostha": "ব্যবস্থা", "babosthar": "ব্যবস্থার", "byabostha": "ব্যবস্থা", "byabosthar": "ব্যবস্থার",
    "baboharer": "ব্যবহারের", "byaboharer": "ব্যবহারের",
    "baboharik": "ব্যবহারিক", "byaboharik": "ব্যবহারিক",
    "sadharonoto": "সাধারণত", "shadharonoto": "সাধারণত",
    "proyojon": "প্রয়োজন", "proyojone": "প্রয়োজনে",
    "jogajog": "যোগাযোগ", "jogajoger": "যোগাযোগের",
    "dayitto": "দায়িত্ব", "dayitwo": "দায়িত্ব", "dayitva": "দায়িত্ব",
    "poristhiti": "পরিস্থিতি", "poristhitir": "পরিস্থিতির",
    "shadhinota": "স্বাধীনতা", "sadhinota": "স্বাধীনতা",
    "bisshash": "বিশ্বাস", "bisshashi": "বিশ্বাসী",
    "attiyo": "আত্মীয়", "attiyo-shojon": "আত্মীয়স্বজন",
    "onnay": "অন্যায়", "onnanno": "অন্যান্য",
    "shomossa": "সমস্যা", "somossa": "সমস্যা",
    "shomadhan": "সমাধান", "somadhan": "সমাধান",
    "proshno": "প্রশ্ন", "uttor": "উত্তর",
    "shikkha": "শিক্ষা", "shikkhito": "শিক্ষিত",
    "juktoborno": "যুক্তবর্ণ", "jukto-borno": "যুক্তবর্ণ",
    "attobisshash": "আত্মবিশ্বাস", "atmobisshash": "আত্মবিশ্বাস",
    "attobishwas": "আত্মবিশ্বাস", "atmobishwas": "আত্মবিশ্বাস",
    "attobissas": "আত্মবিশ্বাস", "atmobissas": "আত্মবিশ্বাস",
    "attobishshash": "আত্মবিশ্বাস", "atmobishshash": "আত্মবিশ্বাস",
    "bishshash": "বিশ্বাস", "bisshash": "বিশ্বাস", "biswas": "বিশ্বাস",
    "shikkha": "শিক্ষা", "sikkha": "শিক্ষা", "shikkharthi": "শিক্ষার্থী",
    "jukto": "যুক্ত", "jukto_borno": "যুক্তবর্ণ", "juktoborno": "যুক্তবর্ণ",
    "uccaron": "উচ্চারণ", "uchcharon": "উচ্চারণ",
    "ovvash": "অভ্যাস", "obvash": "অভ্যাস",
    "onnanno": "অন্যান্য", "onnano": "অন্যান্য",
    "nirvul": "নির্ভুল", "nirbhul": "নির্ভুল",
    "poramorsho": "পরামর্শ",
    "projukti": "প্রযুক্তি", "projokti": "প্রযুক্তি",
    "software": "সফটওয়্যার", "keyboard": "কিবোর্ড",
    "typing": "টাইপিং", "voice": "ভয়েস", "offline": "অফলাইন",
    "online": "অনলাইন", "internet": "ইন্টারনেট",
    "shobdo": "শব্দ", "word": "ওয়ার্ড", "suggestion": "সাজেশন",
    "suggestions": "সাজেশন", "intelligent": "ইন্টেলিজেন্ট",
    "experience": "এক্সপেরিয়েন্স", "user": "ইউজার",
    "bondho": "বন্ধ", "shuru": "শুরু", "korun": "করুন",

    # English loanword: guess / guessing. These are common Banglish spellings
    # for the Bengali-script loanword "গেসিং"; do not let fuzzy neighbours win.
    "guess": "গেস", "guese": "গেস", "ges": "গেস",
    "guessing": "গেসিং", "guissing": "গেসিং", "gessing": "গেসিং",
    "gesing": "গেসিং", "guesing": "গেসিং", "guessin": "গেসিং",
    "gueseing": "গেসিং", "guesingg": "গেসিং",
    "step": "স্টেপ", "steps": "স্টেপস", "stepping": "স্টেপিং",

    # সাধুভাষা / literary Bengali forms. Keep distinct from চলিত forms.
    "sadhubhasha": "সাধুভাষা", "shadhubhasha": "সাধুভাষা",
    "sadhubhasa": "সাধুভাষা", "shadhubhasa": "সাধুভাষা",
    "sadhubhashay": "সাধুভাষায়", "shadhubhashay": "সাধুভাষায়",
    # Common English technology and workplace terms / loanwords.
    "app": "অ্যাপ", "apps": "অ্যাপস", "application": "অ্যাপ্লিকেশন",
    "applications": "অ্যাপ্লিকেশনসমূহ", "account": "অ্যাকাউন্ট",
    "accounts": "অ্যাকাউন্ট", "login": "লগইন", "logout": "লগআউট",
    "website": "ওয়েবসাইট", "websites": "ওয়েবসাইট",
    "browser": "ব্রাউজার", "chrome": "ক্রোম", "extension": "এক্সটেনশন",
    "extensions": "এক্সটেনশন", "profile": "প্রোফাইল", "dashboard": "ড্যাশবোর্ড",
    "interface": "ইন্টারফেস", "design": "ডিজাইন", "developer": "ডেভেলপার",
    "development": "ডেভেলপমেন্ট", "programming": "প্রোগ্রামিং",
    "project": "প্রজেক্ট", "projects": "প্রজেক্ট",
    "feature": "ফিচার", "features": "ফিচার",
    "problem": "সমস্যা", "issue": "ইস্যু", "error": "এরর",
    "support": "সাপোর্ট", "message": "মেসেজ", "notification": "নোটিফিকেশন",
    "settings": "সেটিংস", "setting": "সেটিংস", "keyboard": "কিবোর্ড",
    "microphone": "মাইক্রোফোন", "audio": "অডিও", "video": "ভিডিও",
    "camera": "ক্যামেরা", "file": "ফাইল", "folder": "ফোল্ডার",
    "download": "ডাউনলোড", "upload": "আপলোড", "install": "ইনস্টল",
    "installer": "ইনস্টলার", "update": "আপডেট", "backup": "ব্যাকআপ",
    "performance": "পারফরম্যান্স", "optimization": "অপটিমাইজেশন",
    "optimize": "অপটিমাইজ", "accurate": "অ্যাকুরেট", "accuracy": "অ্যাকুরেসি",
    "prediction": "প্রেডিকশন", "suggestion": "সাজেশন", "suggestions": "সাজেশন",
    "latency": "লেটেন্সি", "response": "রেসপন্স", "startup": "স্টার্টআপ",
    "battery": "ব্যাটারি", "memory": "মেমোরি", "processor": "প্রসেসর",
    "business": "বিজনেস", "businesses": "বিজনেস",
    "customer": "কাস্টমার", "customers": "কাস্টমার",
    "marketing": "মার্কেটিং", "campaign": "ক্যাম্পেইন",
    "content": "কনটেন্ট", "meeting": "মিটিং", "team": "টিম",
    "document": "ডকুমেন্ট", "report": "রিপোর্ট", "invoice": "ইনভয়েস",
}
ALIASES = {k.lower(): unicodedata.normalize("NFC", v) for k, v in ALIASES.items()}

# ---------------------------------------------------------------- Bengali morphology
# A compact offline rule layer. It composes common verb stems with productive
# Bengali endings instead of requiring every inflected form to be memorized.
# Root variants are included because Banglish commonly omits/changes h, sh, y.
MORPH_ROOTS = {
    "likh": "লিখ", "lik": "লিখ",
    "kor": "কর", "k": "ক",
    "bol": "বল",
    "par": "পার",
    "dekh": "দেখ", "dek": "দেখ",
    "shun": "শুন", "sun": "শুন",
    "bujh": "বুঝ", "buj": "বুঝ",
    "jan": "জান",
    "rak": "রাখ", "rakh": "রাখ",
    "uth": "উঠ",
    "bosh": "বস", "bos": "বস",
    "nach": "নাচ",
    "hash": "হাস", "has": "হাস",
    "kand": "কাঁদ",
    "khel": "খেল",
    "por": "পড়", "pOr": "পড়",
    "ja": "যা",
    "as": "আস",
    "ho": "হ",
    "thak": "থাক",
    "dao": "দে", "de": "দে",
    "ne": "নে", "ni": "নি",
    "kha": "খা",
    "ch": "চ",
}

# Longest suffix first. The suffix renderer uses the root ending to distinguish
# forms such as করিতেছে (কর + িতেছে) from যাইতেছে (যা + ইতেছে).
MORPH_SUFFIXES = (
    ("itechilam", "িতেছিলাম"), ("itechilen", "িতেছিলেন"),
    ("itechile", "িতেছিলে"), ("itechilo", "িতেছিল"),
    ("techilam", "তেছিলাম"), ("techilen", "তেছিলেন"),
    ("techile", "তেছিলে"), ("techilo", "তেছিল"),
    ("itechhilo", "িতেছিল"), ("techhilo", "তেছিল"),
    ("itechhilen", "িতেছিলেন"), ("techhilen", "তেছিলেন"),
    ("itechhen", "িতেছেন"),
    ("itechhi", "িতেছি"), ("itechhe", "িতেছে"),
    ("itechen", "িতেছেন"), ("itechi", "িতেছি"),
    ("iteche", "িতেছে"), ("iyachhi", "িয়াছি"),
    ("iyachhe", "িয়াছে"), ("iyachi", "িয়াছি"),
    ("iyache", "িয়াছে"), ("tesen", "তেছেন"),
    ("tesi", "তেছি"), ("tese", "তেছে"),
    ("techen", "ছেন"), ("techi", "ছি"), ("teche", "ছে"),
    ("chhen", "ছেন"), ("chhi", "ছি"), ("chhe", "ছে"),
    ("ite", "িতে"), ("ibo", "িব"), ("iben", "িবেন"),
    ("ibe", "িবে"), ("ite", "িতে"),
    ("bo", "ব"), ("ben", "বেন"), ("be", "বে"),
    ("chi", "ছি"), ("che", "ছে"), ("chen", "ছেন"),
    ("te", "তে"),
)

def morphological_candidates(raw, style="mixed"):
    """Generate common Bengali verb inflections from reusable roots/endings."""
    word = (raw or "").lower()
    if not word.isascii() or not word.isalpha() or len(word) < 4:
        return []
    found = []
    for suffix, ending in MORPH_SUFFIXES:
        if not word.endswith(suffix):
            continue
        stem = word[:-len(suffix)]
        if not stem:
            continue
        root = MORPH_ROOTS.get(stem)
        if not root:
            continue
        if ending.startswith("ি") and root[-1] in "ািীুূেৈোৌ":
            ending = "ই" + ending[1:]
        candidate = unicodedata.normalize("NFC", root + ending)
        if candidate not in found:
            found.append(candidate)

        # For progressive endings, generate equivalent registers. This is
        # deterministic orthographic morphology, not a generative AI guess.
        register_endings = {
            "tesi": {"colloquial": "তেছি", "standard": "ছি", "sadhu": "িতেছি"},
            "tese": {"colloquial": "তেছে", "standard": "ছে", "sadhu": "িতেছে"},
            "tesen": {"colloquial": "তেছেন", "standard": "ছেন", "sadhu": "িতেছেন"},
            "techi": {"colloquial": "তেছি", "standard": "ছি", "sadhu": "িতেছি"},
            "teche": {"colloquial": "তেছে", "standard": "ছে", "sadhu": "িতেছে"},
            "techen": {"colloquial": "তেছেন", "standard": "ছেন", "sadhu": "িতেছেন"},
            "itechhi": {"colloquial": "তেছি", "standard": "ছি", "sadhu": "িতেছি"},
            "itechhe": {"colloquial": "তেছে", "standard": "ছে", "sadhu": "িতেছে"},
            "itechen": {"colloquial": "তেছেন", "standard": "ছেন", "sadhu": "িতেছেন"},
            "itechi": {"colloquial": "তেছি", "standard": "ছি", "sadhu": "িতেছি"},
            "iteche": {"colloquial": "তেছে", "standard": "ছে", "sadhu": "িতেছে"},
            "ite": {"colloquial": "তে", "standard": "তে", "sadhu": "িতে"},
        }
        if suffix in register_endings:
            options = register_endings[suffix]
            if style in options:
                endings = [options[style]]
            else:
                endings = [options["colloquial"], options["standard"], options["sadhu"]]
            for alt_ending in endings:
                if alt_ending.startswith("ি") and root[-1] in "ািীুূেৈোৌ":
                    alt_ending = "ই" + alt_ending[1:]
                alt = unicodedata.normalize("NFC", root + alt_ending)
                if alt not in found:
                    found.append(alt)

    # Irregular high-frequency forms whose stems change in modern Bengali.
    irregular = {
        "jaitesi": {"mixed": "যাইতেছি", "colloquial": "যাইতেছি", "standard": "যাচ্ছি", "sadhu": "যাইতেছি"},
        "jaitese": {"mixed": "যাইতেছে", "colloquial": "যাইতেছে", "standard": "যাচ্ছে", "sadhu": "যাইতেছে"},
        "jaitesen": {"mixed": "যাইতেছেন", "colloquial": "যাইতেছেন", "standard": "যাচ্ছেন", "sadhu": "যাইতেছেন"},
        "jaitechhen": {"mixed": "যাইতেছেন", "colloquial": "যাইতেছেন", "standard": "যাচ্ছেন", "sadhu": "যাইতেছেন"},
        "jaiteche": {"mixed": "যাইতেছে", "colloquial": "যাইতেছে", "standard": "যাচ্ছে", "sadhu": "যাইতেছে"},
        "jaitechhe": {"mixed": "যাইতেছে", "colloquial": "যাইতেছে", "standard": "যাচ্ছে", "sadhu": "যাইতেছে"},
        "jaitechhi": {"mixed": "যাইতেছি", "colloquial": "যাইতেছি", "standard": "যাচ্ছি", "sadhu": "যাইতেছি"},
        "hoiteche": {"mixed": "হইতেছে", "colloquial": "হইতেছে", "standard": "হচ্ছে", "sadhu": "হইতেছে"},
        "hoitechhe": {"mixed": "হইতেছে", "colloquial": "হইতেছে", "standard": "হচ্ছে", "sadhu": "হইতেছে"},
        "hoitechhi": {"mixed": "হইতেছি", "colloquial": "হইতেছি", "standard": "হচ্ছি", "sadhu": "হইতেছি"},
        "jaite": {"mixed": "যাইতে", "colloquial": "যেতে", "standard": "যেতে", "sadhu": "যাইতে"},
        "hoite": {"mixed": "হইতে", "colloquial": "হতে", "standard": "হতে", "sadhu": "হইতে"},
        "korite": {"mixed": "করিতে", "colloquial": "করতে", "standard": "করতে", "sadhu": "করিতে"},
        "parite": {"mixed": "পারিতে", "colloquial": "পারতে", "standard": "পারতে", "sadhu": "পারিতে"},
    }
    if word in irregular:
        preferred = irregular[word].get(style, irregular[word]["mixed"])
        return [preferred]
    if style in ("colloquial", "standard", "sadhu") and found:
        # Register-specific output is the preferred first suggestion.
        if style == "sadhu":
            found.sort(key=lambda x: 0 if any(v in x for v in ("ইতেছি", "ইতেছে", "ইতেছেন", "িতে", "িয়াছে")) else 1)
        elif style == "standard":
            found.sort(key=lambda x: 0 if any(v in x for v in ("ছি", "ছে", "ছেন")) and not any(v in x for v in ("তেছি", "তেছে", "তেছেন")) else 1)
        else:
            found.sort(key=lambda x: 0 if any(v in x for v in ("তেছি", "তেছে", "তেছেন")) else 1)
    return found[:4]


# ---------------------------------------------------------------- phonetic folding
_F = {}
for _c, _k in (
    ("ক", "k"), ("খ", "K"), ("গ", "g"), ("ঘ", "G"), ("ঙ", "M"), ("ং", "M"),
    ("চ", "c"), ("ছ", "c"), ("জ", "j"), ("য", "j"), ("ঝ", "J"), ("ঞ", "n"),
    ("ট", "t"), ("ত", "t"), ("ৎ", "t"), ("ঠ", "T"), ("থ", "T"),
    ("ড", "d"), ("দ", "d"), ("ঢ", "D"), ("ধ", "D"), ("ণ", "n"), ("ন", "n"),
    ("প", "p"), ("ফ", "P"), ("ব", "b"), ("ভ", "B"), ("ম", "m"),
    ("র", "r"), (RRA, "r"), (RHA, "r"), ("ল", "l"), ("শ", "s"), ("ষ", "s"), ("স", "s"),
    ("হ", "h"), (YA, "y"),
    ("আ", "a"), ("া", "a"), ("ই", "i"), ("ঈ", "i"), ("ি", "i"), ("ী", "i"),
    ("উ", "u"), ("ঊ", "u"), ("ু", "u"), ("ূ", "u"), ("ঋ", "R"), ("ৃ", "R"),
    ("এ", "e"), ("ে", "e"), ("ঐ", "I"), ("ৈ", "I"), ("ঔ", "U"), ("ৌ", "U"),
):
    _F[_c] = _k
FOLD_VOWELS = set("aiueIUR")


def fold(s):
    s = s.replace("\u09af\u09bc", YA).replace("\u09a1\u09bc", RRA).replace("\u09a2\u09bc", RHA)
    out = []
    for ch in s:
        c = _F.get(ch)
        if c and (not out or out[-1] != c):
            out.append(c)
    return "".join(out)


def skeleton(key):
    return "".join(c for c in key if c not in FOLD_VOWELS)


def _deletion_signatures(value):
    """Return all one-character deletion signatures (plus the exact key)."""
    out = {value}
    for i in range(len(value)):
        out.add(value[:i] + value[i + 1:])
    return out


def _edit_distance(a, b, cutoff=2):
    """Small-string Levenshtein distance with an early cutoff."""
    if a == b:
        return 0
    if abs(len(a) - len(b)) > cutoff:
        return cutoff + 1
    if len(a) > len(b):
        a, b = b, a
    prev = list(range(len(a) + 1))
    for j, cb in enumerate(b, 1):
        cur = [j]
        row_min = j
        for i, ca in enumerate(a, 1):
            val = min(cur[-1] + 1, prev[i] + 1,
                      prev[i - 1] + (ca != cb))
            cur.append(val)
            row_min = min(row_min, val)
        if row_min > cutoff:
            return cutoff + 1
        prev = cur
    return prev[-1]


def _vdist(a, b):
    a = "".join(c for c in a if c in FOLD_VOWELS)
    b = "".join(c for c in b if c in FOLD_VOWELS)
    if a == b:
        return 0
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


def _keys_for(word):
    k = fold(word)
    keys = {k}
    if "ks" in k:
        keys.add(k.replace("ks", "K"))
    if "jn" in k:
        keys.add(k.replace("jn", "gj"))
    return keys


class Lexicon:
    CACHE_VERSION = 2

    def __init__(self, path, cache_path=None):
        self.freq = {}
        self._cache_path = cache_path
        if cache_path and self._load_cache(path, cache_path):
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                for line in f:
                    p = line.split()
                    if len(p) == 2 and p[1].isdigit() and int(p[1]) >= 4:
                        w = unicodedata.normalize("NFC", p[0])
                        if not _BAD.search(w):
                            self.freq[w] = max(self.freq.get(w, 0), int(p[1]))
        except Exception:
            traceback.print_exc()
        self.by_key = defaultdict(list)
        self.by_skel = defaultdict(list)
        self.by_skel_deletions = defaultdict(set)
        for w, fr in self.freq.items():
            for k in _keys_for(w):
                self.by_key[k].append((w, fr))
        for k, lst in self.by_key.items():
            lst.sort(key=lambda x: -x[1])
            sk = skeleton(k)
            self.by_skel[sk].append((k, lst[0]))
        for sk in self.by_skel:
            for signature in _deletion_signatures(sk):
                self.by_skel_deletions[signature].add(sk)
        self.keys = sorted(self.by_key)
        self._store_cache(path)

    # ------------------------------------------------------------- cache I/O
    @staticmethod
    def _signature(path):
        """Cheap integrity stamp: version + size + content digest."""
        try:
            with open(path, "rb") as handle:
                payload = handle.read()
            digest = hashlib.blake2b(payload, digest_size=12).digest()
            return (Lexicon.CACHE_VERSION, len(payload), digest)
        except Exception:
            return None

    def _load_cache(self, path, cache_path):
        signature = self._signature(path)
        if signature is None:
            return False
        try:
            with open(cache_path, "rb") as handle:
                stamp, freq, by_key, by_skel, by_skel_deletions, keys = marshal.load(handle)
        except Exception:
            return False
        if stamp != signature:
            return False
        self.freq = freq
        self.by_key = defaultdict(list, by_key)
        self.by_skel = defaultdict(list, by_skel)
        self.by_skel_deletions = defaultdict(set, {k: set(v) for k, v in by_skel_deletions.items()})
        self.keys = keys
        return True

    def _store_cache(self, path):
        if not self._cache_path:
            return
        signature = self._signature(path)
        if signature is None:
            return
        try:
            temp = self._cache_path + ".tmp"
            with open(temp, "wb") as handle:
                marshal.dump((signature, self.freq, dict(self.by_key), dict(self.by_skel),
                              {k: tuple(v) for k, v in self.by_skel_deletions.items()},
                              self.keys), handle, 4)
            os.replace(temp, self._cache_path)
        except Exception:
            pass


    def add_word(self, w, fr=60):
        if w in self.freq:
            return
        self.freq[w] = fr
        for k in _keys_for(w):
            lst = self.by_key.get(k)
            if lst is None:
                self.by_key[k] = lst = []
                bisect.insort(self.keys, k)
            lst.append((w, fr))
            lst.sort(key=lambda x: -x[1])
            sk = skeleton(k)
            self.by_skel[sk].append((k, lst[0]))
            for signature in _deletion_signatures(sk):
                self.by_skel_deletions[signature].add(sk)

    def nearby_skeletons(self, sk, max_distance=1, limit=120):
        """Retrieve likely consonant skeleton neighbours without scanning the corpus."""
        found = set()
        for signature in _deletion_signatures(sk):
            found.update(self.by_skel_deletions.get(signature, ()))
            if len(found) >= limit:
                break
        ranked = []
        for candidate in found:
            if candidate == sk:
                continue
            distance = _edit_distance(sk, candidate, max_distance)
            if distance <= max_distance:
                ranked.append((distance, candidate))
        ranked.sort(key=lambda item: (item[0], item[1]))
        return ranked[:limit]

    def prefix(self, key, limit=400):
        i = bisect.bisect_left(self.keys, key)
        out = []
        while i < len(self.keys) and self.keys[i].startswith(key) and len(out) < limit:
            k = self.keys[i]
            if k != key:
                out.append(self.by_key[k][0])
            i += 1
        return out


SEED = {k: unicodedata.normalize("NFC", v) for k, v in SEED.items()}
_BAD = re.compile("অ[\u09be-\u09cc]|আ\u09be|[\u09be-\u09cc]{2}|^[\u09be-\u09cd\u0981-\u0983]|\u09cd$|\u09cd[^\u09a4-\u09b9\u09dc-\u09df\u09af]")


class Engine:
    SEED_VALUES = set(SEED.values())

    def __init__(self, lex_path=None, *, defer=False):
        self.path = os.path.join(config_dir(), "user_dict.json")
        self.user = load_json(self.path, {})
        self.context_path = os.path.join(config_dir(), "context_model.json")
        self.context_model = load_json(self.context_path, {})
        self._candidate_cache = {}
        self._lex_path = lex_path
        self._ready = threading.Event()
        self._thread = None
        self.lex = None
        if not defer:
            self._build_lexicon()
            self._ready.set()

    # ------------------------------------------------------------ warm start
    def _build_lexicon(self):
        here = os.path.dirname(os.path.abspath(__file__))
        source = self._lex_path or os.path.join(here, "bn_words.txt")
        cache = None if self._lex_path else os.path.join(config_dir(), "lexicon-cache.bin")
        lex = Lexicon(source, cache_path=cache)
        for w in self.user.values():
            lex.add_word(w)
        for w in SEED.values():
            lex.add_word(w, 400)
        for w in ALIASES.values():
            lex.add_word(w, 500)
        self.lex = lex
        self._ready.set()

    def warmup(self) -> None:
        """Load the dictionary index off the UI thread (call after first paint)."""
        if self.lex is not None or self._thread is not None:
            return
        self._thread = threading.Thread(target=self._build_lexicon, name="lexicon-warmup",
                                        daemon=True)
        self._thread.start()

    def _ensure_lexicon(self, timeout: float = 4.0) -> bool:
        if self.lex is not None:
            return True
        if self._thread is not None:
            self._ready.wait(timeout)
            return self.lex is not None
        self._build_lexicon()
        return True

    def learn(self, raw, bn, context=None, style="mixed"):
        """Learn accepted spelling and bounded local 1/2-word context signals."""
        if not raw or raw.startswith(";") or not bn:
            return
        changed = self.user.get(raw) != bn
        if changed:
            self.user[raw] = bn
            if self.lex is not None:
                self.lex.add_word(bn)
            save_json(self.path, self.user)

        ctx = [x for x in (context or []) if x][-2:]
        if ctx:
            keys = ["@1:" + ctx[-1]]
            if len(ctx) >= 2:
                keys.append("@2:" + ctx[-2] + "\u241f" + ctx[-1])
            # Keep writing-style preferences separate: conversational choices
            # should not silently train literary/standard suggestions.
            keys.extend("@s:" + style + ":" + key[1:] for key in list(keys))
            for key in keys:
                row = self.context_model.setdefault(key, {})
                row[bn] = min(10000, int(row.get(bn, 0)) + 1)
            # Backward compatibility with V9/V10 two-word and one-word models.
            for legacy in (" ".join(ctx), ctx[-1]):
                if legacy.strip():
                    row = self.context_model.setdefault(legacy, {})
                    row[bn] = min(10000, int(row.get(bn, 0)) + 1)
            # Bound model growth on shared/long-running installations.
            if len(self.context_model) > 5000:
                ranked = sorted(
                    self.context_model.items(),
                    key=lambda item: sum(int(v) for v in item[1].values()),
                    reverse=True
                )
                self.context_model = dict(ranked[:4000])
            save_json(self.context_path, self.context_model)
        self._candidate_cache.clear()

    def _context_rank(self, candidates, context, style):
        """Backoff n-gram reranker; only reorders existing phonetic candidates."""
        ctx = [x for x in (context or []) if x][-2:]
        if not ctx or len(candidates) < 2:
            return candidates
        keys = []
        if len(ctx) >= 2:
            keys.append(("@2:" + ctx[-2] + "\u241f" + ctx[-1], 2.4))
            keys.append((" ".join(ctx), 1.8))  # V9/V10 compatibility
        keys.append(("@1:" + ctx[-1], 1.2))
        keys.append((ctx[-1], 0.8))  # legacy one-word model
        style_keys = [("@s:" + style + ":1:" + ctx[-1], 1.5)]
        if len(ctx) >= 2:
            style_keys.append(("@s:" + style + ":2:" + ctx[-2] + "\u241f" + ctx[-1], 3.0))
        scores = {}
        for key, weight in keys + style_keys:
            row = self.context_model.get(key, {})
            for word in candidates:
                count = int(row.get(word, 0))
                if count:
                    scores[word] = scores.get(word, 0.0) + weight * math.log1p(count)
        if not scores:
            return candidates
        # Stable sort retains phonetic engine order where there is no evidence.
        return sorted(candidates, key=lambda word: -scores.get(word, 0.0))

    def candidates(self, raw, limit=8, context=None, style="mixed"):
        if not self._ensure_lexicon():
            return []
        ctx = tuple((context or [])[-2:])
        key = (raw, limit, ctx, style)
        cached = self._candidate_cache.get(key)
        if cached is not None:
            return list(cached)
        result = self._candidates_uncached(raw, limit, style=style)
        # Context is a backoff language-model signal, never a replacement for
        # a strong exact spelling or curated alias. Only ambiguous candidates
        # can be reordered.
        result = self._context_rank(result, ctx, style)
        if len(self._candidate_cache) >= 512:
            self._candidate_cache.clear()
        self._candidate_cache[key] = tuple(result)
        return list(result)

    def _candidates_uncached(self, raw, limit=8, style="mixed"):
        lex = self.lex
        if lex is None:
            return []
        sc = {}

        def add(w, s):
            if w and sc.get(w, -1e9) < s:
                sc[w] = s

        # Exact, curated and user-confirmed spellings are authoritative.
        # Returning unrelated fuzzy transliterations below these mappings was
        # the source of screenshot errors such as "test" -> several malformed
        # Bengali spellings. Keep the list clean when confidence is explicit.
        # Learned spellings are ranking preferences, not hard locks.
        # Preserve alternatives for ambiguous inputs such as "oke".
        learned = self.user.get(raw)
        s = SEED.get(raw) or SEED.get(raw.lower())
        alias = ALIASES.get(raw.lower())
        if alias:
            return [alias]
        if s:
            return [s]
        morph = morphological_candidates(raw, style=style)
        if morph:
            return morph[:limit]
        # Prefix completion for curated loanwords: after 2 characters, prefer
        # a known lexical completion over unrelated Bengali words with a
        # coincidentally similar phonetic skeleton.
        lower_raw = raw.lower()
        if len(lower_raw) >= 2 and lower_raw.isascii() and lower_raw.isalpha():
            prefix_hits = []
            for roman, bn in ALIASES.items():
                if roman.startswith(lower_raw) and roman != lower_raw:
                    prefix_hits.append((len(roman), roman, bn))
            if prefix_hits:
                prefix_hits.sort(key=lambda item: (item[0], item[1]))
                unique = []
                for _, _, bn in prefix_hits:
                    if bn not in unique:
                        unique.append(bn)
                    if len(unique) >= min(3, limit):
                        break
                # If a prefix has one unambiguous curated completion, use it
                # directly (e.g. "performanc" -> "পারফরম্যান্স").
                if (lower_raw in ("ap", "acc", "bus", "web", "key", "sof")
                        or len(unique) == 1 and len(lower_raw) >= 3):
                    return unique[:limit]
        smart = convert(raw, "smart")
        convs = [smart, convert(raw, "noreph"), convert(raw, "avro")]
        key = fold(convert(raw, "avro"))
        lead_o = raw[:1] in ("o", "O")
        for w, fr in lex.by_key.get(key, [])[:40]:
            pen = 4 if (w[:1] in ("অ", "ও") and not lead_o) else 0
            add(w, 6 + math.log(fr + 1) + (3 if w in self.SEED_VALUES else 0) - pen)
        for i, c in enumerate(convs):
            fr = lex.freq.get(c)
            if fr:
                add(c, 10 + math.log(fr + 1) - i * 0.5)
        # Preserve the user's actual Roman spelling as the primary phonetic
        # interpretation. Fuzzy dictionary neighbours remain alternatives,
        # not replacements (e.g. "khobori" must not silently become "খবর").
        if smart not in lex.freq:
            add(smart, 100.0)
        else:
            add(smart, 18.0 + math.log(lex.freq.get(smart, 1) + 1))
        if len(key) >= 2:
            for w, fr in lex.by_key.get(key, [])[:0]:
                pass
            sk = skeleton(key)
            if len(sk) >= 3:
                cand = []
                # Exact consonant skeletons first, then nearby skeletons that
                # differ by one omitted/extra consonant (e.g. babostha -> ব্যবস্থা).
                nearby = [(0, sk)]
                nearby.extend(lex.nearby_skeletons(sk, max_distance=1, limit=80))
                seen_words = set()
                for consonant_distance, sk2 in nearby:
                    for k2, (w, fr) in lex.by_skel.get(sk2, [])[:12]:
                        if w in seen_words or fr < 12:
                            continue
                        seen_words.add(w)
                        vowel_distance = _vdist(key, k2)
                        # A matching consonant skeleton alone is not enough:
                        # it caused unrelated guesses such as "guissing" ->
                        # "গ্যাং". Require a reasonable vowel match as well.
                        max_vowel_distance = 2 if len(key) >= 7 else 1
                        if vowel_distance > max_vowel_distance:
                            continue
                        score = (7.0 + math.log(fr + 1)
                                 - 3.0 * consonant_distance
                                 - 2.2 * vowel_distance
                                 - 0.35 * abs(len(key) - len(k2)))
                        # Informal Banglish often drops the glide "y" in
                        # bya-/byo- clusters: "babostha" for "byabostha".
                        # Reward a candidate whose য/য় glide follows the
                        # first consonant when the input has that initial.
                        if (consonant_distance and len(sk2) >= 3
                                and sk2[0] == sk[0]
                                and sk2[1] == "j"
                                and len(sk) >= 3):
                            score += 3.5
                        # Users often omit the "w/b" glide in স্ব clusters,
                        # typing "shadhinota" for "স্বাধীনতা".
                        if (consonant_distance and len(sk2) >= 3
                                and sk[0] == "s" and sk2.startswith("sb")
                                and raw.lower().startswith(("sha", "swa", "sho"))):
                            score += 4.5
                        # Bengali ত্ব clusters are frequently typed as "tto"
                        # although the orthographic folded key ends in "tb".
                        if raw.lower().endswith(("tto", "itto")) and k2.endswith("tb"):
                            score += 4.0
                        cand.append((score, w))
                cand.sort(reverse=True)
                for s2, w in cand[:8]:
                    add(w, s2)
            pre = []
            for w, fr in lex.prefix(key):
                if fr >= 30:
                    pre.append((math.log(fr + 1) - 1.5 - 0.25 * (len(fold(w)) - len(key)), w))
            pre.sort(reverse=True)
            for s2, w in pre[:3]:
                add(w, s2)
        # Prefer exact curated mappings and the user's learned spelling over
        # fuzzy dictionary neighbours. Preserve stable ordering for ties.
        out = [w for w, _ in sorted(sc.items(), key=lambda x: -x[1])]
        if len(out) < 3:
            for v in variants(raw):
                c = convert(v, "smart")
                if c not in out:
                    out.append(c)
                if len(out) >= 4:
                    break
        if learned:
            # Promote the accepted spelling without suppressing alternatives.
            out = [learned] + [word for word in out if word != learned]
        return out[:limit]
