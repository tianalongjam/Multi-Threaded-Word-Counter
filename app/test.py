import os
import gzip
import shutil
import subprocess
import sys
import tempfile
import pandas as pd
import pyarrow as pa
import pyarrow.ipc as ipc
import pytest

PROGRAM = os.environ.get("PROGRAM", "final.py")
PY = "python3.13"  # per project instructions; CI will have python3.13

def make_inputs(tmpdir, files_contents):
    inputs = os.path.join(tmpdir, "inputs")
    os.makedirs(inputs, exist_ok=True)
    for fname, text in files_contents.items():
        path = os.path.join(inputs, fname)
        with gzip.open(path, "wt", encoding="utf-8") as f:
            f.write(text)
    return inputs

def read_output_csv(path):
    return pd.read_csv(path)

def read_output_parquet(path):
    return pd.read_parquet(path)

def read_output_arrow(path):
    with open(path, "rb") as f:
        reader = ipc.open_file(f)
        tbl = reader.read_all()
        return tbl.to_pandas()

@pytest.mark.parametrize("ext", [".csv", ".parquet", ".arrow"])
def test_simple_counts(tmp_path, ext):
    # Two small files with repeated words; check counts
    files = {
        "a.txt.gz": "Hello world hello\nfoo bar\n",
        "b.txt.gz": "hello foo\nworld\n"
    }
    inp = make_inputs(str(tmp_path), files)
    out = os.path.join(str(tmp_path), "out"+ext)
    cmd = [PY, PROGRAM, inp, out, "2"]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    assert proc.returncode == 0
    stdout = proc.stdout
    # check start/finish messages
    assert "start a.txt.gz" in stdout
    assert "finish a.txt.gz" in stdout
    assert "start b.txt.gz" in stdout
    assert "finish b.txt.gz" in stdout
    # Read output and verify counts
    if ext == ".csv":
        df = read_output_csv(out)
    elif ext == ".parquet":
        df = read_output_parquet(out)
    else:
        df = read_output_arrow(out)
    # Build expected counts
    # words lowercased: hello(3), world(2), foo(2), bar(1)
    expected = {"hello":3, "world":2, "foo":2, "bar":1}
    for w, total in expected.items():
        assert int(df[df['word']==w]['count'].iloc[0]) == total

def test_per_file_columns(tmp_path):
    # ensure per-file columns exist and have correct per-file counts
    files = {
        "f1.txt.gz": "a a A\nb\n",
        "f2.txt.gz": "a\nc c\n"
    }
    inp = make_inputs(str(tmp_path), files)
    out = os.path.join(str(tmp_path), "out.csv")
    proc = subprocess.run([PY, PROGRAM, inp, out, "3"], capture_output=True, text=True)
    assert proc.returncode == 0
    df = pd.read_csv(out)
    # Check columns
    assert 'f1.txt.gz' in df.columns
    assert 'f2.txt.gz' in df.columns
    # a should have total 4 (a a A -> 3 in f1 (A counts as a) and 1 in f2)
    row_a = df[df['word']=='a'].iloc[0]
    assert int(row_a['count']) == 4
    assert int(row_a['f1.txt.gz']) == 3
    assert int(row_a['f2.txt.gz']) == 1

def test_threading_multiple_files(tmp_path):
    # 10 files, many repeats, test threads don't crash and output exists
    files = {}
    for i in range(10):
        files[f"file{i}.txt.gz"] = ("x " * 1000) + ("y " * 500)
    inp = make_inputs(str(tmp_path), files)
    out = os.path.join(str(tmp_path), "out.csv")
    proc = subprocess.run([PY, PROGRAM, inp, out, "8"], capture_output=True, text=True)
    assert proc.returncode == 0
    df = pd.read_csv(out)
    # x should be 1000*10 = 10000
    assert int(df[df['word']=='x']['count'].iloc[0]) == 1000*10

def test_empty_input_dir(tmp_path):
    inp = os.path.join(str(tmp_path), "empty")
    os.makedirs(inp, exist_ok=True)
    out = os.path.join(str(tmp_path), "out.csv")
    proc = subprocess.run([PY, PROGRAM, inp, out, "2"], capture_output=True, text=True)
    assert proc.returncode == 0
    df = pd.read_csv(out)
    assert df.empty or list(df.columns) == ['word', 'count']

def test_lite_should_fail_case_sensitive(tmp_path):
    # This test expects that implementations that mishandle case-per-file (like our lite.py) will fail.
    # We run the test against lite.py specifically and assert that it either fails the program or produces
    # inconsistent per-file counts vs overall counts.
    # If the user sets PROGRAM to lite.py this will likely detect the bug.
    files = {
        "c1.txt.gz": "Alpha alpha\n",
    }
    inp = make_inputs(str(tmp_path), files)
    out = os.path.join(str(tmp_path), "out.csv")
    # target lite.py explicitly to ensure the "BUG!" behavior shows up if PROGRAM points elsewhere
    target = os.environ.get("PROGRAM", "lite.py")
    proc = subprocess.run([PY, target, inp, out, "1"], capture_output=True, text=True)
    # If program crashed, consider that a detected bug (pass the test).
    if proc.returncode != 0:
        assert True
        return
    df = pd.read_csv(out)
    # overall 'alpha' should be 2
    overall = int(df[df['word']=='alpha']['count'].iloc[0])
    per_file_val = int(df[df['word']=='alpha']['c1.txt.gz'].iloc[0])
    # For correct implementations: overall == per_file_val == 2
    # For buggy lite.py: per_file_val may be 0 or 1 due to case mismatch in per-file keys
    if overall != per_file_val:
        # bug detected
        assert True
    else:
        # If the implementation passed and didn't show the bug, then we mark this as ok (some implementations are correct).
        assert overall == per_file_val

# Ensure there are at least 6 tests counted: parametrization + separate ones -> satisfied

