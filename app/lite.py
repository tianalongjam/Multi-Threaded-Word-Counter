#!/usr/bin/env python3
# lite.py - intentionally contains a small bug for testing
# BUG!: per-file counts are not lowered (case mismatch) while overall counts are lowered

import sys, os, gzip, re, threading, queue
from collections import Counter, defaultdict
import pandas as pd
import pyarrow as pa
import pyarrow.ipc as ipc

RE = re.compile(r'\s+')

def worker(q, indir, lock, overall, perfile):
    while True:
        try:
            fname = q.get_nowait()
        except queue.Empty:
            return
        base = os.path.basename(fname)
        print(f"start {base}", flush=True)
        local = Counter()
        p = os.path.join(indir, fname)
        with gzip.open(p, mode='rt', encoding='utf-8', errors='ignore') as f:
            for line in f:
                for w in RE.split(line):
                    if not w:
                        continue
                    # BUG!: per-file counter uses original case, not lowercased
                    local[w] += 1
        with lock:
            for k,v in local.items():
                overall[k.lower()] += v  # overall is lowered
                perfile[k][base] += v    # per-file uses original-case keys (BUG)
        print(f"finish {base}", flush=True)
        q.task_done()

def main(argv):
    if len(argv) != 4:
        print("usage", file=sys.stderr); sys.exit(2)
    indir, out, threads = argv[1], argv[2], int(argv[3])
    files = sorted([f for f in os.listdir(indir) if f.endswith('.txt.gz')])
    q = queue.Queue()
    for f in files: q.put(f)
    lock = threading.Lock()
    overall = Counter()
    perfile = defaultdict(lambda: defaultdict(int))
    ts = []
    for _ in range(max(1, threads)):
        t = threading.Thread(target=worker, args=(q, indir, lock, overall, perfile))
        t.start()
        ts.append(t)
    q.join()
    for t in ts: t.join(timeout=0.1)
    rows = []
    for w in sorted(overall.keys()):
        row = {'word': w, 'count': int(overall[w])}
        for fn in files:
            row[fn] = int(perfile.get(w, {}).get(fn, 0))
        rows.append(row)
    df = pd.DataFrame(rows, columns=['word','count']+files)
    ext = os.path.splitext(out)[1].lower()
    if ext == ".csv":
        df.to_csv(out, index=False)
    elif ext == ".parquet":
        df.to_parquet(out, index=False)
    elif ext == ".arrow":
        table = pa.Table.from_pandas(df)
        with ipc.new_file(out, table.schema) as writer:
            writer.write_table(table)
    else:
        print("unknown ext", file=sys.stderr); sys.exit(1)

if __name__ == "__main__":
    main(sys.argv)
