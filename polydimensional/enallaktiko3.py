import time
import tracemalloc
import math
from dataclasses import dataclass
from typing import List, Tuple
from statistics import median

import numpy as np
import pandas as pd


# -----------------------------
# Config
# -----------------------------
CSV_PATH = "movies_metadata.csv"

# sizes to test (set None to skip benchmarking by sizes)
BENCH_SIZES = [5_000, 10_000, 20_000, 30_000, 40_000, None]

# If your CSV uses different column names, change here:
COL_BUDGET = "budget"
COL_POP = "popularity"
COL_TITLE = "title"  # optional






# -----------------------------
# Utilities
# -----------------------------
def safe_numeric(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce")


def load_and_clean(csv_path: str) -> pd.DataFrame:
    """
    Loads CSV and returns a cleaned dataframe with at least:
      budget, popularity
    """
    df = pd.read_csv(csv_path, low_memory=False)

    if COL_BUDGET not in df.columns or COL_POP not in df.columns:
        raise ValueError(
            f"CSV must contain columns '{COL_BUDGET}' and '{COL_POP}'. "
            f"Found columns: {list(df.columns)[:30]} ..."
        )

    df = df.copy()
    df[COL_BUDGET] = safe_numeric(df[COL_BUDGET])
    df[COL_POP] = safe_numeric(df[COL_POP])

    df = df.dropna(subset=[COL_BUDGET, COL_POP])

    # Optional sanity filters (budgets/popularity should be >= 0)
    df = df[(df[COL_BUDGET] >= 0) & (df[COL_POP] >= 0)]

    return df


def make_subsample(df: pd.DataFrame, n: int, seed: int = 42) -> pd.DataFrame:
    if n >= len(df):
        return df
    return df.sample(n=n, random_state=seed)


# -----------------------------
# Timing helper (median of repeats)
# -----------------------------
def median_time_ms(fn, repeat: int = 5, warmup: int = 1) -> float:
    # warmup
    for _ in range(warmup):
        fn()

    times = []
    for _ in range(repeat):
        t0 = time.perf_counter()
        fn()
        t1 = time.perf_counter()
        times.append((t1 - t0) * 1000.0)

    return float(median(times))


# -----------------------------
# Convex Hull (Monotonic Chain)
# -----------------------------
def cross(o: Tuple[float, float], a: Tuple[float, float], b: Tuple[float, float]) -> float:
    return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])


def convex_hull(points: np.ndarray) -> np.ndarray:
    """
    points: (n,2) array of floats
    returns hull vertices (h,2) in CCW order (no repeated start/end)

    Complexity: O(n log n) (sorting dominates)
    """
    if points.size == 0:
        return points

    pts = np.unique(points, axis=0)
    if len(pts) <= 1:
        return pts

    pts = pts[np.lexsort((pts[:, 1], pts[:, 0]))]
    pts_list = [tuple(p) for p in pts]

    lower: List[Tuple[float, float]] = []
    for p in pts_list:
        while len(lower) >= 2 and cross(lower[-2], lower[-1], p) <= 0:
            lower.pop()
        lower.append(p)

    upper: List[Tuple[float, float]] = []
    for p in reversed(pts_list):
        while len(upper) >= 2 and cross(upper[-2], upper[-1], p) <= 0:
            upper.pop()
        upper.append(p)

    hull = lower[:-1] + upper[:-1]
    return np.array(hull, dtype=float)


# -----------------------------
# Skyline (Sort + Scan)
# -----------------------------
def skyline_sort_scan(df: pd.DataFrame) -> pd.DataFrame:
    """
    Skyline for MIN budget, MAX popularity
    Time: O(n log n)
    """
    cols = [COL_BUDGET, COL_POP] + ([COL_TITLE] if COL_TITLE in df.columns else [])
    d = df[cols].copy()

    # sort: budget ASC, popularity DESC
    d = d.sort_values([COL_BUDGET, COL_POP], ascending=[True, False])

    best_pop = -np.inf
    keep_pos = []

    for i, pop in enumerate(d[COL_POP].to_numpy()):
        if pop > best_pop:
            keep_pos.append(i)
            best_pop = pop

    return d.iloc[keep_pos].reset_index(drop=True)

def write_skyline_sql(path: str = "skyline_predicate.sql") -> None:
    sql_text = f"""
-- Skyline for: MIN {COL_BUDGET}, MAX {COL_POP}
SELECT m.*
FROM movies m
WHERE NOT EXISTS (
  SELECT 1
  FROM movies m2
  WHERE
    m2.{COL_BUDGET} <= m.{COL_BUDGET}
    AND m2.{COL_POP} >= m.{COL_POP}
    AND (m2.{COL_BUDGET} < m.{COL_BUDGET} OR m2.{COL_POP} > m.{COL_POP})
)
ORDER BY m.{COL_BUDGET} ASC, m.{COL_POP} DESC;
""".strip()

    with open(path, "w", encoding="utf-8") as f:
        f.write(sql_text + "\n")

# -----------------------------
# Benchmarking (time + memory)
# -----------------------------
@dataclass
class BenchResult:
    n: int
    hull_vertices: int
    skyline_size: int
    hull_time_ms: float
    sky_time_ms: float
    peak_mem_kb: int


def bench_one(df: pd.DataFrame, repeat: int = 3, warmup: int = 1) -> BenchResult:
    pts = df[[COL_BUDGET, COL_POP]].to_numpy(dtype=float)

    # -------- time (NO tracemalloc) --------
    hull_container = {"hull": None}
    def run_hull():
        hull_container["hull"] = convex_hull(pts)

    sky_container = {"sky": None}
    def run_sky():
        sky_container["sky"] = skyline_sort_scan(df)

    hull_time = median_time_ms(run_hull, repeat=repeat, warmup=warmup)
    hull = hull_container["hull"]

    sky_time = median_time_ms(run_sky, repeat=repeat, warmup=warmup)
    sky = sky_container["sky"]

    # -------- memory (single run WITH tracemalloc) --------
    tracemalloc.start()
    _ = convex_hull(pts)
    _ = skyline_sort_scan(df)
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    return BenchResult(
        n=len(df),
        hull_vertices=len(hull),
        skyline_size=len(sky),
        hull_time_ms=hull_time,
        sky_time_ms=sky_time,
        peak_mem_kb=int(peak / 1024),
    )


# -----------------------------
# Main
# -----------------------------
def main():
    df = load_and_clean(CSV_PATH)
    write_skyline_sql()
    print("Saved SQL predicate to: skyline_predicate.sql")
    print("Loaded rows (clean):", f"{len(df):,}")
    print("P1 = {(budget, popularity)}  (each point = (budget, popularity))")

    

    results: List[BenchResult] = []

    for size in BENCH_SIZES:
        if size is None:
            df_test = df
            label = "FULL"
        else:
            df_test = make_subsample(df, size)
            label = f"{size:,}"

        r = bench_one(df_test, repeat=5, warmup=1)
        results.append(r)

        print(
            f"[n={label}] hull_vertices={r.hull_vertices:,} | skyline={r.skyline_size:,} "
            f"| hull={r.hull_time_ms:.2f} ms | skyline={r.sky_time_ms:.2f} ms | peak_mem≈{r.peak_mem_kb:,} KB"
        )

    sky_full = skyline_sort_scan(df)
    print("\n" + "=" * 60)
    print("Skyline (MIN budget, MAX popularity) — first 25 rows:")
    cols = [c for c in [COL_TITLE, COL_BUDGET, COL_POP] if c in sky_full.columns]
    print(sky_full[cols].head(25).to_string(index=False))

    out_path = "skyline_minBudget_maxPopularity.csv"
    sky_full.to_csv(out_path, index=False)
    print(f"\nSaved skyline to: {out_path}")

    bench_df = pd.DataFrame([r.__dict__ for r in results])
 


    # Experimental proof: O(n log n) normalization
    bench_df["nlogn"] = bench_df["n"].apply(lambda x: x * math.log2(x))
    bench_df["hull_norm"] = bench_df["hull_time_ms"] / bench_df["nlogn"]
    bench_df["sky_norm"] = bench_df["sky_time_ms"] / bench_df["nlogn"]

    print("\nNormalized times (time / (n log2 n)) — should be ~constant if O(n log n):")
    print(bench_df[["n", "hull_norm", "sky_norm"]].to_string(index=False))

    bench_out = "benchmark_q3.csv"
    bench_df.to_csv(bench_out, index=False)
    print(f"\nSaved benchmark results to: {bench_out}")


if __name__ == "__main__":
    main()
