#!/usr/bin/env python3
# flash.py - functional variant (intended to mimic flash model output)

import sys, os, gzip, re, threading, queue
from collections import Counter, defaultdict
import pandas as pd
import pyarrow as pa
import pyarrow.ipc as ipc

SPLIT_RE = re.compile(r'\s+')

def process_file(path, base):
    c = Counter()
    with gzip.open(path, mode='rt', encoding='utf-8', errors='ignore') as f:
        for line in f:
            for w in SPLIT_RE.split(line):
                if w:
                    c[w.lower()] += 1
    return c

def worker(q, indir, lock, overall, perfile):
    while True:
        try:
            fname = q.get_nowait()
        except queue.Empty:
            return
        base = os.path.basename(fname)
        print(f"start {base}", flush=True)
        local = process_file(os.path.join(indir, fname), base)
        with lock:
            for k,v in local.items():
                overall[k] += v
                perfile[k][base] += v
        print(f"finish {base}", flush=True)
        q.task_done()

def main(argv):
    if len(argv) != 4:
        print("Usage: python3 flash.py <indir> <out> <threads>", file=sys.stderr); sys.exit(2)
    indir, out, threads_s = argv[1], argv[2], argv[3]
    threads = int(threads_s)
    files = sorted([f for f in os.listdir(indir) if f.endswith('.txt.gz')])
    if not files:
        pd.DataFrame(columns=['word','count']).to_csv(out, index=False)
        return
    q = queue.Queue()
    for f in files: q.put(f)
    lock = threading.Lock()
    overall = Counter()
    perfile = defaultdict(lambda: defaultdict(int))
    ts = []
    for _ in range(threads):
        t = threading.Thread(target=worker, args=(q, indir, lock, overall, perfile))
        t.start()
        ts.append(t)
    q.join()
    for t in ts: t.join(timeout=1.0)
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
        print("unknown out ext", file=sys.stderr); sys.exit(1)

if __name__ == "__main__":
    main(sys.argv)
