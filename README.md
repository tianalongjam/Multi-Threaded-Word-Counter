# Multi-Threaded Word Counter

## Overview

This project explores concurrent programming, AI-assisted code generation, and performance benchmarking in Python. The system processes compressed text files using multi-threading, counts word frequencies across files, exports results in multiple formats, and evaluates performance under different runtime configurations.

The project compares AI-generated implementations from multiple models and benchmarks execution under standard Python (GIL) and Python nogil.

## Features

- Multi-threaded word counting
- Support for compressed `.txt.gz` input files
- Output formats:
  - CSV
  - Parquet
  - Arrow
- Per-file and global word frequency counts
- AI-generated implementations comparison:
  - Gemini 2.5 Pro
  - Gemini 2.5 Flash
  - Gemini 2.5 Flash Lite
- Pytest test suite
- Thread performance benchmarking:
  - Python with GIL
  - Python without GIL
- Format benchmarking:
  - CSV vs Parquet vs Arrow

---
## Thread Benchmarking

![Thread Benchmarking](/outputs/threads.png)
---

## Repository Structure

```txt

Dockerfile

app/
├── final.py
├── pro.py
├── Dockerfile
├── flash.py
├── lite.py
├── test.py
├── thread_bench.py
└── format_bench.py

inputs/
├── file1.txt.gz
└── file2.txt.gz

outputs/
├── out_1.csv
├── out_2.csv
├── out_4.csv
├── output.arrow 
├── output.csv
├── output.parquet
├── test.arrow 
├── test.csv
├── test.parquet
├── threads.csv
├── threads.svg
├── formats.csv
└── formats.svg
```

---

## Installation

Clone repository:

```bash
git clone <repo-url>
cd <repo-name>
```

Build Docker image:

```bash
docker build -t p-wordcount .
```

---

## Running Word Count

Run with Python 3.13:

```bash
docker run \
-v ./inputs:/inputs \
-v ./outputs:/outputs \
p-wordcount \
python3.13 app/final.py \
/inputs \
/outputs/output.csv \
4
```

Run with Python nogil:

```bash
docker run \
-v ./inputs:/inputs \
-v ./outputs:/outputs \
p-wordcount \
python3.13-nogil app/final.py \
/inputs \
/outputs/output.parquet \
8
```

Arguments:

```txt
<input_directory>
<output_file>
<threads>
```

---

## Running Tests

Execute pytest:

```bash
docker run \
-e PROGRAM=final.py \
p-wordcount \
python3.13 -m pytest /app/test.py
```

Example:

```bash
docker run \
-e PROGRAM=pro.py \
p-wordcount \
python3.13 -m pytest /app/test.py
```

---

## Thread Benchmarking

Generate benchmark outputs:

```bash
docker run \
-v ./outputs:/outputs \
p-wordcount \
python3.13 app/thread_bench.py /outputs
```

Outputs:

- `threads.csv`
- `threads.svg`

Metrics:

- Number of threads
- Runtime with GIL
- Runtime without GIL

---

## Format Benchmarking

Run:

```bash
docker run \
-v ./outputs:/outputs \
p-wordcount \
python3.13 app/format_bench.py /outputs
```

Outputs:

- `formats.csv`
- `formats.svg`

Benchmarks compare:

- CSV read performance
- Parquet selective column reads
- Arrow memory-mapped reads

---

## Testing Coverage

The test suite validates:

- Correct word counts
- Thread safety
- Output formats
- Edge cases
- AI-generated implementation failures
- Benchmark reproducibility

---

## AI Models Evaluated

- Gemini 2.5 Pro
- Gemini 2.5 Flash
- Gemini 2.5 Flash Lite

The final implementation (`final.py`) was selected after evaluating correctness, performance, and robustness.

---

## Technologies Used

- Python 3.13
- Python nogil
- Docker
- Pytest
- Pandas
- PyArrow
- Parquet
- CSV
- Multi-threading
