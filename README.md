# Infinity GPU Miner

A **heavily optimized** OpenCL miner for solving the [Infinity Token](https://github.com/8finity-xyz/protocol) Proof-of-Work **Magic XOR** problem.  

> **Acknowledgment**  
> This miner is based on the [profanity2](https://github.com/1inch/profanity2) approach, with special modifications to handle Infinity’s `MagicXOR` puzzle. Many thanks to the original profanity2 developers for the incredible optimizations.

---

## 1. Installation

### 1.1 Dependencies & Platforms & Notes

This miner is a heavily optimized software, hence it is quite picky dependencies-wise. Please make sure you have all the necessary dependancies installed and working together.

**An optimal option for most of the users will be to proceed with Docker build on a server with NVIDIA GPU.**

- **OpenCL** (SDK + GPU drivers)  
  - Linux: `ocl-icd-opencl-dev`, `libopencl-clang-dev`, compatible NVIDIA or AMD drivers
  - macOS: OpenCL must be available; Apple Silicon with GPU drivers (Metal/OpenCL bridging) tested.
- **C++11** compiler (e.g., `g++`).
- **Python 3.10+** with `pybind11`, `safe-pysha3`, `ecdsa`, `coincurve`, `web3`, `websockets`, etc.
- **Make** (for building `magicXorMiner.so`).
- (Optional) **Docker** (for container builds).

> **Tested** primarily on Linux (NVIDIA GPUs) and Apple Silicon. Other platforms *may* work but are not guaranteed.

The code includes two Makefiles:
- `Makefile` for **Linux**
- `Makefile.mac` for **macOS**  

### 1.2 Linux Build

There are **three** common ways to build on Linux:

1. **Hardcore:** Bare-metal installation:
<details>
    <summary>Hardcore version</summary>

```bash
   # Install dependencies, for example on Ubuntu:
   sudo apt-get update && sudo apt-get install -y \
    g++ make git ocl-icd-opencl-dev libopencl-clang-dev curl python3 python3-pip clinfo nano

    # Install Python packages for Python 3.10
   pip3 install pybind11 safe-pysha3 ecdsa web3 coincurve websocket-client websockets dotenv 

   # Clone and build:
   git clone https://github.com/otonashi-labs/pow.git
   cd pow
   make clean && make

   # Potentially you might wanna use this line. If Nvidia and OpenCL aren't befrending
   # Configure OpenCL ICD for NVIDIA
   # mkdir -p /etc/OpenCL/vendors && echo "libnvidia-opencl.so.1" > /etc/OpenCL/vendors/nvidia.icd

   # test that OpenCL is indeed working under the hood
   python3 test_opencl_kernel.py 

   # mine (but please do some setup first and congrats if this option succeded 🎉)
   python3 mine_infinity.py
```

This will likely produce `magicXorMiner.so`, with high probability.

However, there might be platform specific issues.  If experiencing any trouble with installing all of the dependancies -- please consider Docker build. 

**THIS IS THE HARDCORE BUILD VERSION**

</details>


2. **Recommended:** Build with Docker, using the provided Dockerfile:
```bash
    # build
    docker build -t infinity-gpu-miner .
    
    # Then run with GPU passthrough (e.g. NVIDIA Docker setup):
    docker run --gpus all -it infinity-gpu-miner /bin/bash

    # all repository files will be already there
    cd /app

    # test that OpenCL is indeed working under the hood
    python3 test_opencl_kernel.py 

    # mine (but please do some setup first)
    python3 mine_infinity.py
 ```

Inside the container you’ll find the compiled `magicXorMiner.so` in /app.

3. **Simplest Possible:** Pull prebuilt container from Docker Hub:
```bash
    docker pull devoak/magic-xor-miner:nvidia-latest
```
Then run:
```bash
    docker run --gpus all -it devoak/magic-xor-miner:nvidia-latest-stats /bin/bash

    cd /app

    # test that OpenCL is indeed working under the hood
    python3 test_opencl_kernel.py 
    
    # mine (but please do some setup first)
    python3 mine_infinity.py

```
The container already includes everything needed.

**NOTE: Ensure your Docker runtime and driver stack are set up to allow GPU access.**

### 1.3 macOS Build

macOS support is tested primarily on Apple Silicon (M1/M2). Adjust paths and frameworks for your environment.

To build:
```bash
    git clone https://github.com/otonashi-labs/pow.git
    cd pow
    chmod +x build_mac.sh
    ./build_mac.sh

    # pay attention to any possible Error messages, ideally you will NOT get any
    # warning messages are OKAY

    # test that OpenCL is indeed working under the hood and that the build is succesefull
    python3 test_opencl_kernel.py 
    
    # mine (but please do some setup first)
    python3 mine_infinity.py
```

This should produce `magicXorMiner.so.`

**NOTE: This is the only way to launch miner on MacOs. Docker build DOES NOT work on Mac Os.**

### 1.4 Hosting on Vast.ai

If you don’t have a local GPU, you can deploy your build (or the prebuilt Docker image) onto Vast.ai. While renting a machine with GPU support, upload/pull the container and run the same steps (create your own template there to do that).

---

## 2. Usage
1.	Edit `.env.example` with your actual Infinity addresses/keys:

`MASTER_ADDRESS` and `MASTER_PKEY` (the wallet that pays gas and signs solutions).

`REWARDS_RECIPIENT_ADDRESS` (where your miner’s block rewards go).

`INFINITY_RPC` and `INFINITY_WS` - Sonic blockchain connections (you can use default ones as well)

2.	Rename to `.env` or export those variables in your environment.

*NOTE: `nano .env.example` and do all the changes inside; then `mv .env.example .env` will do the job*

3.	Run the miner: `python3 mine_infinity.py`, which:

Security Warning
**This code is not designed with heavy security in mind; it’s best practice to use a dedicated wallet for mining with minimal funds.**

---

## 3. Tweaking / Advanced

Within `config.py`, you’ll find configuration options:

```python
# You can provide custom data for the signature (EIP-191)
SIGN_DATA = bytes.fromhex("deadbeef1337cafebabe")  # Must be ≤ 32 bytes

# [TX-BUILDER] - Gas fees
# You can create your own strategy for gas fees!
MAX_PRIORITY_FEE_MWEI = 500
BASE_FEE_K = 2

# [MINER] - Profanity2-like GPU tuning
# Experiment with these values to find the optimal hashrate for your hardware.
WORKSIZE_LOCAL = 64               # OpenCL local work size
WORKSIZE_MAX = 0                  # 0 => default = INVERSE_SIZE * INVERSE_MULTIPLE
INVERSE_SIZE = 255                # how many modular inversions per work item
INVERSE_MULTIPLE = 1024           # how many parallel items to run
PROFANITY2_VERBOSE_FLAG = False   # do you want profanity2 working logs?
MINER_VERBOSE_FLAG = True         # don't toggle these both to True -- they will mix, one at a time please
```

---

License & Credits
- This tool is adapted from 1inch/profanity2, all related disclaimers apply.
- No warranties. Use responsibly. Infinity GPU Miner authors are not liable for any damages or losses.


Enjoy mining Infinity — and if you discover improvements or have questions, feel free to open an issue or a pull request.

