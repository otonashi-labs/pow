# Infinity GPU Miner

A **heavily optimized** OpenCL miner for solving the [Infinity Token](https://github.com/8finity-xyz/protocol) Proof-of-Work **Magic XOR** problem.  

> **Acknowledgment**  
> This miner is based on the [profanity2](https://github.com/1inch/profanity2) approach, with special modifications to handle Infinity’s `MagicXOR` puzzle. Many thanks to the original profanity2 developers for the incredible optimizations.

---

## 1. Overview

The Infinity PoW mechanic ([PoW.sol](https://github.com/8finity-xyz/protocol/blob/main/contracts/PoW.sol)) requires finding a private key **B** (`privateKeyB`) such that:

`(uint160(addressAB ^ MAGIC_NUMBER) < difficulty)`ß

Where:
- `addressAB` is derived from `publicKeyAB`, which is in turn derived by summing two private keys (`privateKeyA + privateKeyB` mod `0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEFFFFFC2F`).
- `MAGIC_NUMBER = 0x8888888888888888888888888888888888888888`
- `difficulty` is a 160-bit value controlling the submission rate and puzzle hardness. (e.g. `0x00000000ffffffffffffffffffffffffffffffff`)

This repository provides:
- OpenCL kernels (`profanity.cl` + custom `magicxor` kernel) for computing bazillions of candidate solutions in parallel.
- A Python-based framework (`mine_infinity.py`) for automatically:
  - Listening to new puzzle parameters (`privateKeyA`, `difficulty`) from Infinity’s contract events.
  - Polling `MASTER_ADDRESS` nonce and `eth_feeHistory` for tx building.
  - Mining solutions on the GPU.
  - Submitting solutions via Ethereum-like transactions to the Sonic blockchain.

**Disclaimer**: This is highly optimized code that *cuts corners* for performance. **Always** verify any discovered key in a safe environment if you plan to actually use it, but better never use discovered keys for storing value. Use a dedicated wallet for mining.

---

## 2. Installation

### 2.1 Dependencies & Platforms

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

### 2.2 Linux Build

There are **three** common ways to build on Linux:

1. **Bare-metal** environment:
```bash
   # Install dependencies, for example on Ubuntu:
   sudo apt-get update && sudo apt-get install -y \
       g++ make git ocl-icd-opencl-dev libopencl-clang-dev python3 python3-pip

   # Clone and build:
   git clone https://github.com/otonashi-labs/pow.git
   cd pow
   make clean && make
```

This will produce `magicXorMiner.so`.

2. Build with Docker, using the provided Dockerfile:
```bash
    # build
    docker build -t infinity-gpu-miner .
    
    # Then run with GPU passthrough (e.g. NVIDIA Docker setup):
    docker run --gpus all -it infinity-gpu-miner /bin/bash
 ```

Inside the container you’ll find the compiled `magicXorMiner.so` in /app.

3. Pull prebuilt container from Docker Hub:
```bash
    docker pull otonashi_labs/magic-xor-miner:latest
```
Then run:
```bash
    docker run --gpus all -it otonashi_labs/magic-xor-miner:latest /bin/bash
```
The container already includes everything needed.

**NOTE: Ensure your Docker runtime and driver stack are set up to allow GPU access.**

### 2.3 macOS Build

macOS support is tested primarily on Apple Silicon (M1/M2). Adjust paths and frameworks for your environment.

Within Makefile.mac, you’ll see:

```makefile
    CC = g++

    CDEFINES = -I/opt/homebrew/lib/python3.11/site-packages/pybind11/include
    CDEFINES += -I/opt/homebrew/opt/python@3.11/Frameworks/Python.framework/Versions/3.11/include/python3.11

    LDFLAGS = -framework OpenCL \
            -L/opt/homebrew/opt/python@3.11/Frameworks/Python.framework/Versions/3.11/lib \
            -lpython3.11

```
You must confirm the include/linker paths match where your Python 3.11 and pybind11 are installed. 
Commonly:
1.  Headers live in `/opt/homebrew/lib/python3.11/site-packages/pybind11/include`
2.  Python 3.11 frameworks in `/opt/homebrew/opt/python@3.11/Frameworks/Python.framework/Versions/3.11`

To build:
```bash
    make -f Makefile.mac clean && make -f Makefile.mac && make -f Makefile.mac clean
```

This should produce `magicXorMiner.so.`

**NOTE: This is the only way to launch miner on MacOs. Docker build DOES NOT work on Mac Os.**

### 2.4 Hosting on Vast.ai

If you don’t have a local GPU, you can deploy your build (or the prebuilt Docker image) onto Vast.ai. While renting a machine with GPU support, upload/pull the container and run the same steps (create your own template there to do that).

⸻

### 3. Usage
1.	Edit `.env.example` with your actual Infinity addresses/keys:

`MASTER_ADDRESS` and `MASTER_PKEY` (the wallet that pays gas and signs solutions).
`REWARDS_RECIPIENT_ADDRESS` (where your miner’s block rewards go).

2.	Rename to `.env` or export those variables in your environment.

3.	Check the Infinity RPC/WS endpoints in mine_infinity.py:

`INFINITY_RPC = 'https://rpc.blaze.soniclabs.com'`
`INFINITY_WS  = 'wss://rpc.blaze.soniclabs.com'`

4.	Run the miner: `python3 mine_infinity.py`, which:

    1. Connects to Sonic chain.
    2. Listens for NewProblem events (restarts search on NewProblem event).
    3. Polls state for tx-building (nonce & eth_feeHistory)
    4. Offloads GPU hashing to find privateKeyB.
    5. Submits a solution once found. 
        

Security Warning
**This code is not designed with heavy security in mind; it’s best practice to use a dedicated wallet for mining with minimal funds.**
⸻

### 5. Tweaking / Advanced

Within `mine_infinity.py`, you’ll find configuration options:

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

⸻

License & Credits
	•	This tool is adapted from 1inch/profanity2, all related disclaimers apply.
	•	No warranties. Use responsibly. Infinity GPU Miner authors are not liable for any damages or losses.

Enjoy mining Infinity — and if you discover improvements or have questions, feel free to open an issue or a pull request.

