"""
Benchmark: furigana_service_original vs furigana_service_optimized

Run from the project root:
    python benchmark_furigana.py
"""
import sys
import time

sys.path.insert(0, ".")

print("Loading modules (MeCab init may take a moment)...")
import app.services.furigana_service_original as orig
import app.services.furigana_service_optimized as opt

# ── Test data ────────────────────────────────────────────────────────────────

SHORT = "日本語"
MEDIUM = "今日は天気がいいですね。私は学校に行きます。"
LONG = (
    "東京都は日本の首都であり、世界最大の都市圏の一つです。"
    "江戸時代から続く歴史ある文化と、最先端の技術が共存しています。"
    "毎年多くの観光客が日本各地から訪れ、伝統的な祭りや食文化を楽しんでいます。"
)
KANJI_HEAVY = "漢字変換処理速度測定用文章。文字認識機能最適化実験。"
REPEATED = SHORT  # same text repeated — maximum cache benefit

BATCH_VARIED = [SHORT, MEDIUM, LONG, KANJI_HEAVY] * 5          # 20 items, varied
BATCH_REPEATED = [REPEATED] * 20                                 # 20 items, identical

# ── Benchmark helpers ────────────────────────────────────────────────────────

def measure(fn, *args, repeat: int = 10) -> float:
    """Return mean wall-clock time in milliseconds over `repeat` runs."""
    # warm-up run (not counted)
    fn(*args)
    start = time.perf_counter()
    for _ in range(repeat):
        fn(*args)
    return (time.perf_counter() - start) / repeat * 1000


def measure_cold(fn, *args) -> float:
    """Single cold run in milliseconds (no cache warm-up)."""
    start = time.perf_counter()
    fn(*args)
    return (time.perf_counter() - start) * 1000


def speedup(orig_ms: float, opt_ms: float) -> str:
    if opt_ms == 0:
        return "∞x"
    ratio = orig_ms / opt_ms
    return f"{ratio:.2f}x"


# ── Run benchmarks ───────────────────────────────────────────────────────────

print("Running benchmarks...\n")

results: list[tuple[str, float, float]] = []

def add(label: str, o_ms: float, p_ms: float) -> None:
    results.append((label, o_ms, p_ms))

# 1. Cold start — first call ever (caches empty for optimized)
o = measure_cold(orig.add_furigana, SHORT)
p = measure_cold(opt.add_furigana, SHORT)
add("Short — cold start", o, p)

# 2. Short text, warm (repeated calls, cache fills up)
o = measure(orig.add_furigana, SHORT, repeat=50)
p = measure(opt.add_furigana, SHORT, repeat=50)
add("Short — warm (×50)", o, p)

# 3. Medium text, warm
o = measure(orig.add_furigana, MEDIUM, repeat=30)
p = measure(opt.add_furigana, MEDIUM, repeat=30)
add("Medium — warm (×30)", o, p)

# 4. Long text, warm
o = measure(orig.add_furigana, LONG, repeat=20)
p = measure(opt.add_furigana, LONG, repeat=20)
add("Long — warm (×20)", o, p)

# 5. Kanji-heavy text, warm
o = measure(orig.add_furigana, KANJI_HEAVY, repeat=20)
p = measure(opt.add_furigana, KANJI_HEAVY, repeat=20)
add("Kanji-heavy — warm (×20)", o, p)

# 6. Hiragana-only mode, medium text
o = measure(orig.add_furigana, MEDIUM, "hiragana_only", repeat=30)
p = measure(opt.add_furigana, MEDIUM, "hiragana_only", repeat=30)
add("Hiragana-only mode — warm (×30)", o, p)

# 7. Batch — varied texts
o = measure(orig.add_furigana_batch, BATCH_VARIED, repeat=5)
p = measure(opt.add_furigana_batch, BATCH_VARIED, repeat=5)
add("Batch varied (20 items, ×5)", o, p)

# 8. Batch — repeated identical text (maximum cache benefit)
o = measure(orig.add_furigana_batch, BATCH_REPEATED, repeat=5)
p = measure(opt.add_furigana_batch, BATCH_REPEATED, repeat=5)
add("Batch repeated (20×same, ×5)", o, p)

# ── Print table ──────────────────────────────────────────────────────────────

col_label  = 34
col_num    = 14
col_speed  = 9

header = (
    f"{'Test Case':<{col_label}}"
    f"{'Original (ms)':>{col_num}}"
    f"{'Optimized (ms)':>{col_num}}"
    f"{'Speedup':>{col_speed}}"
)
sep = "-" * len(header)

print(sep)
print(header)
print(sep)
for label, o_ms, p_ms in results:
    print(
        f"{label:<{col_label}}"
        f"{o_ms:>{col_num}.2f}"
        f"{p_ms:>{col_num}.2f}"
        f"{speedup(o_ms, p_ms):>{col_speed}}"
    )
print(sep)

# Cache stats for optimized module
print()
print("lru_cache statistics (optimized):")
for fn_name in ("_pykakasi_hira", "_single_char_hira", "_reading_hints", "_reading_variants"):
    fn = getattr(opt, fn_name)
    info = fn.cache_info()
    hit_rate = info.hits / (info.hits + info.misses) * 100 if (info.hits + info.misses) else 0
    print(f"  {fn_name:<22} hits={info.hits:>5}  misses={info.misses:>4}  hit_rate={hit_rate:.1f}%")
