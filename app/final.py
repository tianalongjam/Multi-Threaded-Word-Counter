#!/usr/bin/env python3
"""
final.py - Multi-threaded word count per spec

Usage:
    python3 final.py <input_directory> <output_file> <threads>
"""

import sys
import os
import gzip
import re
import threading
import queue
from collections import Counter, defaultdict
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import pyarrow.ipc as ipc

WORD_RE = re.compile(r'\s+')

def file_worker(file_q, input_dir, global_lock, overall_counter, per_file_counters):
    while True:
        try:
            fname = file_q.get_nowait()
        except queue.Empty:
            return

        base = os.path.basename(fname)
        print(f"start {base}", flush=True)
        local_counter = Counter()
        path = os.path.join(input_dir, fname)

        try:
            with gzip.open(path, mode="rt", encoding="utf-8", errors="ignore") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    words = WORD_RE.split(line)
                    for w in words:
                        if w:
                            local_counter[w.lower()] += 1
        except Exception as e:
            print(f"error reading {base}: {e}", file=sys.stderr)

        with global_lock:
            for w, c in local_counter.items():
                overall_counter[w] += c
                per_file_counters[w][base] += c

        print(f"finish {base}", flush=True)
        file_q.task_done()


def write_output_csv(df, out_path):
    df.to_csv(out_path, index=False)


def write_output_parquet(df, out_path):
    df.to_parquet(out_path, index=False)


def write_output_arrow(df, out_path):
    table = pa.Table.from_pandas(df)
    with ipc.new_file(out_path, table.schema) as writer:
        writer.write_table(table)


def build_dataframe(overall_counter, per_file_counters, filenames_sorted):
    words = sorted(overall_counter.keys())
    rows = []
    for w in words:
        row = {"word": w, "count": int(overall_counter[w])}
        pf = per_file_counters.get(w, {})
        for fn in filenames_sorted:
            row[fn] = int(pf.get(fn, 0))
        rows.append(row)

    df = pd.DataFrame(rows)
    cols = ["word", "count"] + filenames_sorted
    return df[cols]


def main(argv):
    if len(argv) != 4:
        print("Usage: python3 final.py <input_directory> <output_file> <threads>", file=sys.stderr)
        sys.exit(2)

    input_dir, output_file, threads_s = argv[1], argv[2], argv[3]

    try:
        threads = int(threads_s)
        if threads < 1:
            raise ValueError()
    except ValueError:
        print("threads must be a positive integer", file=sys.stderr)
        sys.exit(2)

    # ✅ Only read .txt.gz files (ignore any output files accidentally left in input_dir)
    files = sorted([
        f for f in os.listdir(input_dir)
        if f.endswith(".txt.gz") and os.path.isfile(os.path.join(input_dir, f))
    ])

    # No input files → create empty output
    if not files:
        df_empty = pd.DataFrame(columns=["word", "count"])
        ext = os.path.splitext(output_file)[1].lower()
        if ext == ".csv":
            write_output_csv(df_empty, output_file)
        elif ext == ".parquet":
            write_output_parquet(df_empty, output_file)
        elif ext == ".arrow":
            write_output_arrow(df_empty, output_file)
        else:
            print(f"Unknown output extension: {ext}", file=sys.stderr)
            sys.exit(1)
        return

    file_q = queue.Queue()
    for f in files:
        file_q.put(f)

    global_lock = threading.Lock()
    overall_counter = Counter()
    per_file_counters = defaultdict(lambda: defaultdict(int))

    workers = []
    for _ in range(threads):
        t = threading.Thread(
            target=file_worker,
            args=(file_q, input_dir, global_lock, overall_counter, per_file_counters),
            daemon=True
        )
        t.start()
        workers.append(t)

    # Wait until queue is done
    file_q.join()

    for t in workers:
        t.join(timeout=1.0)

    filenames_sorted = sorted(files)
    df = build_dataframe(overall_counter, per_file_counters, filenames_sorted)

    ext = os.path.splitext(output_file)[1].lower()
    if ext == ".csv":
        write_output_csv(df, output_file)
    elif ext == ".parquet":
        write_output_parquet(df, output_file)
    elif ext == ".arrow":
        write_output_arrow(df, output_file)
    else:
        print(f"Unknown output extension: {ext}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main(sys.argv)

