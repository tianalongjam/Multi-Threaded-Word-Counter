#!/usr/bin/env python3
import os
import sys
import gzip
import random
import string
import time
import subprocess
import pandas as pd
import matplotlib.pyplot as plt
import pyarrow.parquet as pq
import pyarrow as pa

def make_inputs(input_dir, n_files=256, vocab_size=1000, words_per_file=1_000_000):
    """Generate input files only if none exist."""
    os.makedirs(input_dir, exist_ok=True)
    existing_files = [f for f in os.listdir(input_dir) if f.endswith(".txt.gz")]
    if len(existing_files) >= n_files:
        print(f"Found {len(existing_files)} input files in {input_dir}, skipping generation.")
        return

    print(f"Generating {n_files} input files in {input_dir}...")
    vocab = ["".join(random.choices(string.ascii_lowercase, k=6)) for _ in range(vocab_size)]
    for i in range(n_files):
        fname = os.path.join(input_dir, f"file_{i:03d}.txt.gz")
        if os.path.exists(fname):
            continue
        with gzip.open(fname, "wt", encoding="utf-8") as f:
            for _ in range(words_per_file // 10):
                line = " ".join(random.choices(vocab, k=10))
                f.write(line + "\n")
        if (i + 1) % 25 == 0:
            print(f"  → finished {i+1}/{n_files} files")
    print("✅ Input generation complete.")

def measure_read_time(path, fmt):
    start = time.perf_counter()
    if fmt == "csv":
        df = pd.read_csv(path, usecols=["count"])
        _ = df["count"].sum()
    elif fmt == "parquet":
        df = pd.read_parquet(path, columns=["count"])
        _ = df["count"].sum()
    elif fmt == "arrow":
        with pa.memory_map(path, "r") as source:
            table = pa.ipc.open_file(source).read_all()
            _ = table.column("count").to_pandas().sum()
    return time.perf_counter() - start

def main():
    if len(sys.argv) != 2:
        print("Usage: python3.13 format_bench.py <output_dir>")
        sys.exit(1)

    base_output = os.path.abspath(sys.argv[1])
    input_dir = os.path.join(base_output, "inputs")
    output_dir = os.path.join(base_output, "format_outputs")
    os.makedirs(output_dir, exist_ok=True)

    make_inputs(input_dir)

    formats = ["csv", "parquet", "arrow"]
    times = []

    for fmt in formats:
        print(f"\n=== Running format: {fmt} ===")
        out_path = os.path.join(output_dir, f"data.{fmt}")
        subprocess.run(["python3.13", "final.py", input_dir, out_path, "4"], check=True)
        t = measure_read_time(out_path, fmt)
        times.append({"format": fmt, "read_seconds": t})
        print(f"Done {fmt}: {t:.3f} s")

    df = pd.DataFrame(times)
    df.to_csv(os.path.join(base_output, "formats.csv"), index=False)

    plt.figure(figsize=(6, 4))
    plt.bar(df["format"], df["read_seconds"])
    plt.ylabel("Read Time (s)")
    plt.xlabel("Format")
    plt.title("Read Performance by Format")
    plt.grid(True, axis="y")
    plt.savefig(os.path.join(base_output, "formats.svg"), bbox_inches="tight")

    print("\n✅ Benchmark complete! Results saved to formats.csv and formats.svg")

if __name__ == "__main__":
    main()

