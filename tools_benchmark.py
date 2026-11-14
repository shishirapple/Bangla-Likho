# -*- coding: utf-8 -*-
import json, os, sys, time
from engine import Engine

here = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(here, "benchmark_banglish_v1.json"), encoding="utf-8") as f:
    data = json.load(f)
engine = Engine(os.path.join(here, "bn_words.txt"))
passed = 0
total_ms = 0.0
for raw, expected in data["cases"]:
    start = time.perf_counter()
    got = engine.candidates(raw, 5)
    elapsed = (time.perf_counter() - start) * 1000
    total_ms += elapsed
    ok = bool(got) and got[0] == expected
    passed += int(ok)
    print(("PASS" if ok else "FAIL"), raw, "=>", got[:3], "| expected:", expected, "| %.3f ms" % elapsed)
print("Top-1: %d/%d (%.1f%%)" % (passed, len(data["cases"]), 100*passed/len(data["cases"])))
print("Mean candidate latency: %.3f ms" % (total_ms/len(data["cases"])))
