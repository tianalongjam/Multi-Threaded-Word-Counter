# --------------------------------------------------------------------
# CS544 Project 3 - Python 3.13 (with and without GIL)
# --------------------------------------------------------------------
FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHON_VERSION=3.13.0
WORKDIR /tmp

# --------------------------------------------------------------------
# Install system dependencies
# --------------------------------------------------------------------
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential wget curl git ca-certificates libssl-dev zlib1g-dev \
    libbz2-dev libreadline-dev libsqlite3-dev libffi-dev libncursesw5-dev \
    libgdbm-dev liblzma-dev tk-dev xz-utils pkg-config \
    && rm -rf /var/lib/apt/lists/*

# --------------------------------------------------------------------
# Download and build CPython 3.13 (regular version)
# --------------------------------------------------------------------
RUN wget -q https://www.python.org/ftp/python/${PYTHON_VERSION}/Python-${PYTHON_VERSION}.tgz \
    && tar xzf Python-${PYTHON_VERSION}.tgz

WORKDIR /tmp/Python-${PYTHON_VERSION}
RUN ./configure --enable-optimizations --with-ensurepip=install \
    && make -j$(nproc) \
    && make altinstall

# --------------------------------------------------------------------
# Build CPython 3.13 *no-GIL* version
# --------------------------------------------------------------------
WORKDIR /tmp/Python-${PYTHON_VERSION}
RUN ./configure --disable-gil --with-ensurepip=install --prefix=/opt/python3.13-nogil \
    && make -j$(nproc) \
    && make install

# Add no-GIL version to PATH
RUN ln -s /opt/python3.13-nogil/bin/python3.13 /usr/local/bin/python3.13-nogil \
    && ln -s /opt/python3.13-nogil/bin/pip3 /usr/local/bin/pip3-nogil

# Verify Python installations
RUN /usr/local/bin/python3.13 --version && /usr/local/bin/python3.13-nogil --version

# --------------------------------------------------------------------
# Copy app code
# --------------------------------------------------------------------
WORKDIR /app
COPY app/ /app/
COPY requirements-dev.txt /app/requirements-dev.txt

# --------------------------------------------------------------------
# Install Python packages for both builds
# --------------------------------------------------------------------
RUN /usr/local/bin/python3.13 -m pip install --upgrade pip setuptools wheel \
    && /usr/local/bin/python3.13 -m pip install -r /app/requirements-dev.txt \
    && /usr/local/bin/python3.13 -m pip install matplotlib pytest pandas pyarrow fastparquet \
    && /usr/local/bin/python3.13-nogil -m pip install --upgrade pip setuptools wheel \
    && /usr/local/bin/python3.13-nogil -m pip install -r /app/requirements-dev.txt \
    && /usr/local/bin/python3.13-nogil -m pip install matplotlib pytest pandas pyarrow fastparquet

# --------------------------------------------------------------------
# Prepare I/O directories
# --------------------------------------------------------------------
RUN mkdir -p /inputs /outputs

# --------------------------------------------------------------------
# Default command
# --------------------------------------------------------------------
CMD ["/usr/local/bin/python3.13", "thread_bench.py", "/outputs"]

