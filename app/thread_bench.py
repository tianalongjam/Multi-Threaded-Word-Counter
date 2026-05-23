import os, gzip, random, string, time, subprocess, pandas as pd, matplotlib.pyplot as plt, shutil
from pathlib import Path

def gen_inputs(input_dir):
    # Remove any old input files to avoid permission issues
    if input_dir.exists():
        shutil.rmtree(input_dir)
    input_dir.mkdir(exist_ok=True)

    vocab = ["".join(random.choices(string.ascii_lowercase, k=5)) for _ in range(1000)]
    print("Generating benchmark input files...")
    for i in range(256):
        with gzip.open(input_dir / f"file{i}.txt.gz", "wt") as f:
            for _ in range(1_000_000):
                f.write(random.choice(vocab) + "\n")
    print("Input generation complete.")

def bench(py_exec, threads_list, outputs_dir):
    times = []
    input_dir = outputs_dir / "bench_inputs"
    gen_inputs(input_dir)

    for t in threads_list:
        out_file = outputs_dir / f"out_{t}.csv"
        print(f"Running benchmark: {py_exec} with {t} thread(s)...")
        start = time.time()
        subprocess.run([py_exec, "final.py", str(input_dir), str(out_file), str(t)], check=True)
        elapsed = time.time() - start
        times.append(elapsed)
        print(f"Done in {elapsed:.2f} seconds.")
    return times

def main():
    import sys, shutil
    out_dir = Path(sys.argv[1])
    out_dir.mkdir(exist_ok=True)

    threads = [1, 2, 4, 8]
    gil_times = bench("python3.13", threads, out_dir)

    if shutil.which("python3.13-nogil"):
        nogil_times = bench("python3.13-nogil", threads, out_dir)
    else:
        print(" python3.13-nogil not found — skipping no-GIL benchmarks.")
        nogil_times = [None] * len(threads)

    df = pd.DataFrame({
        "threads": threads,
        "gil_seconds": gil_times,
        "nogil_seconds": nogil_times
    })
    df.to_csv(out_dir / "threads.csv", index=False)
    print("Saved results to threads.csv")

    plt.plot(df["threads"], df["gil_seconds"], label="GIL")
    if any(nogil_times):
        plt.plot(df["threads"], df["nogil_seconds"], label="no-GIL")
    plt.xlabel("Threads")
    plt.ylabel("Seconds")
    plt.legend()
    plt.title("Thread Scaling Benchmark")
    plt.savefig(out_dir / "threads.svg")
    print("Saved plot to threads.svg")

if __name__ == "__main__":
    main()

