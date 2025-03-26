FROM ubuntu:22.04
ENV DEBIAN_FRONTEND=noninteractive
WORKDIR /app


# Install dependencies and Python 3.11, remove Python 3.10
RUN apt-get update && apt-get install -y \
    software-properties-common && \
    add-apt-repository ppa:deadsnakes/ppa -y && \
    apt-get update && apt-get install -y \
    g++ \
    make \
    python3.11 \
    python3.11-dev \
    python3-pip \
    libopencl-clang-dev \
    ocl-icd-opencl-dev \
    git \
    curl && \
    # Remove Python 3.10 and its dependencies
    apt-get remove -y python3.10 python3-pip && \
    # Install pip for Python 3.11 explicitly
    curl -sSL https://bootstrap.pypa.io/get-pip.py -o get-pip.py && \
    python3.11 get-pip.py && \
    rm get-pip.py && \
    # Set Python 3.11 as the default python3
    update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.11 1 && \
    # Symlink pip3 to Python 3.11's pip
    ln -sf /usr/local/bin/pip3.11 /usr/bin/pip3 && \
    # Clean up
    apt-get autoremove -y && \
    rm -rf /var/lib/apt/lists/*


# Install Python packages for Python 3.11
RUN python3.11 -m pip install --no-cache-dir \
    pybind11 \
    safe-pysha3 \
    ecdsa

COPY . ./

# make considering pybind installation 
# could be replaced in the future once pybind11 is located
RUN PYBIND11_INCLUDE=$(python3.11 -c "import pybind11; print(pybind11.get_include())") && \
    echo "Pybind11 include path: $PYBIND11_INCLUDE" && \
    make clean && make \
    CFLAGS="-c -std=c++11 -Wall -O2 -fPIC" \
    LDFLAGS="-shared -lOpenCL" \
    CDEFINES="-I/usr/include/python3.11 -I$PYBIND11_INCLUDE"

# Default command: Run a Python shell for testing
CMD ["/bin/bash"]