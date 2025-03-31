from ecdsa import SigningKey, SECP256k1
import magicXorMiner
from web3 import Web3
from eth_account.messages import encode_defunct
from eth_account import Account
import json
import requests
import sha3 # pip install safe-pysha3
import time
import coincurve
from eth_account.messages import defunct_hash_message
import multiprocessing
import random
import copy
from eth_abi import decode  
from websocket import create_connection  
import threading
import queue


"""
    Config
"""
WEB3_IDLE_PROVIDER = Web3()

ALCHEMY_URL = 'http://127.0.0.1:8545'
CHAIN_ID = 146
POW_CONTRACT = "0x9fE46736679d2D9a65F0992F2272dE9f3c7fa6e0"
POW_NEW_PROBLEM_TOPIC0 = "0xd24ba3f407317c41a60dd7cf9f4ed40e425a44fbb60b68b9438832eba981a0c5"
SESSION = requests.Session()

PKEY_A_SELECTOR = "0xb4ffbbc8"
DIFF_SELECTOR = "0x19cae462"
GAS_LIMIT_SUBMIT = 2_000_000

# be creative, pick your own data, don't make it too long though,
# code will compulsory fail if len(SIGN_DATA) > 32
# so, keep that in mind
SIGN_DATA = bytes.fromhex("deadbeef1337cafebabe")

# you could optionally choose a different address for the rewards
MASTER_ADDRESS = "0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266"
MASTER_PKEY = "0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80"
REWARDS_RECIPIENT_ADDRESS = "0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266"

# feel free to tune it
MAX_PRIORITY_FEE_MWEI = 500
BASE_FEE_K = 2

# Mining params section:
# feel free to tweak this parameters until it works the best for you
# original profanity2 params are mirrored here: https://github.com/1inch/profanity2
"""
Tweaking:
    -w, --work <size>       Set OpenCL local work size. [default = 64]
    -W, --work-max <size>   Set OpenCL maximum work size. [default = -i * -I]
    -i, --inverse-size      Set size of modular inverses to calculate in one
                            work item. [default = 255]
    -I, --inverse-multiple  Set how many above work items will run in
                            parallell. [default = 16384]
"""
WORKSIZE_LOCAL = 64
WORKSIZE_MAX = 0  # 0 means default
INVERSE_SIZE = 255
INVERSE_MULTIPLE = 1024
PROFANITY2_VERBOSE_FLAG = False  # do you want profanity2 working logs?
MINER_VERBOSE_FLAG = True


"""
    Async miner logic

    think if we need mutex
"""

current_miner_process = None
last_privateKeyA = None


"""
    [UTILS]
    get public key on the secp256k1 elliptic curve

    private_key_hex -- hex no '0x'
"""
def get_secp256k1_pub(private_key_hex):
    sk = SigningKey.from_string(string = bytes.fromhex(private_key_hex), curve=SECP256k1)
    vk = sk.verifying_key
    public_key_bytes = vk.to_string()
    public_key_hex = public_key_bytes.hex()
    return public_key_hex


"""
    [UTILS]
    get public key POINT on the secp256k1 elliptic curve

    private_key_hex -- hex no '0x'
"""
def get_ecc_point(private_key_hex):
    public_key_hex = get_secp256k1_pub(private_key_hex)
    x_hex = public_key_hex[:64] 
    y_hex = public_key_hex[64:] 
    x = int(x_hex, 16)
    y = int(y_hex, 16)
    return x, y

"""
    [UTILS]

    Sum of two pkeys could start with leading zero bytes, which is inacceptable for next modules in a line

    hence --> fix
"""
def _pkey_paddding_hex(uint256_hex):
    numba = uint256_hex[2:]
    padd_n = 64 - len(numba)
    return "0x" + padd_n * "0" + numba

"""
    [UTILS]
    sum to private keys

    pkey_a_hex, pkey_b_hex -- hex no '0x'
"""
def get_pkeys_sum(pkey_a_hex, pkey_b_hex):
    pkey_a = int("0x" + pkey_a_hex, 16)
    pkey_b = int("0x" + pkey_b_hex, 16)
    pkey_full = hex((pkey_a + pkey_b) % 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEFFFFFC2F)
    return _pkey_paddding_hex(pkey_full)


"""
    [UTILS][TX-BUILDER]

    sign in PoW.sol specific format

    private_key_ab_hex -- accepts both WITH and WITHOUT "0x"

    Works around 5ms 
    Much simpler to use, because it is basically a part of web3py
    feel free to fallback to this option if optimized one doesn't work!
"""
# def create_signature_ab(
#         private_key_ab_hex, 
#         recipient, 
#         data
#     ):
#     recipient = WEB3_IDLE_PROVIDER.to_checksum_address(recipient)
#     message_hash = WEB3_IDLE_PROVIDER.solidity_keccak(
#         ['address', 'bytes'],
#         [recipient, data]
#     )
#     eip191_message = encode_defunct(primitive=message_hash)
#     signed_message = Account.sign_message(
#         eip191_message,
#         private_key=private_key_ab_hex
#     )
    
#     r = hex(signed_message.r)
#     s = hex(signed_message.s)
#     v = hex(signed_message.v)
#     return r, s, v


"""
    [UTILS][TX-BUILDER]

    sign in PoW.sol specific format

    private_key_ab_hex -- no "0x"

    Optimized verison, works around 1 ms

    recipient HAS to be checksumed address!

    if you have any promlem with coincurve library (it's not always easy to install -- uncomment and use the function above)
"""
def create_signature_ab(
        private_key_ab_hex,
        recipient,
        data
    ):
    private_key_bytes = bytes.fromhex(private_key_ab_hex)
    message_hash = WEB3_IDLE_PROVIDER.solidity_keccak(
        ['address', 'bytes'],
        [recipient, data]
    )
    eip191_message_hash = defunct_hash_message(primitive=message_hash)  
    private_key = coincurve.PrivateKey(private_key_bytes)
    signature = private_key.sign_recoverable(eip191_message_hash, hasher=None)
    r = hex(int.from_bytes(signature[:32], 'big'))
    s = hex(int.from_bytes(signature[32:64], 'big'))
    v = hex(signature[64] + 27)
    
    return r, s, v


"""
    [DATA][STATE-LOADING]
    Build calldata for rpc-multicall
"""
def get_essential_state_multicall_params(
        master_address,
        pow_address
    ):
    nonce_req = {
        "id": "nonce_req",
        "jsonrpc": "2.0",
        "params": [
            master_address,
            "latest"
        ],
        "method": "eth_getTransactionCount"
    }
    
    gas_req = {
        "method" : "eth_feeHistory",
        "jsonrpc" : "2.0",
        "params" : ["0x5", "latest", []],
        "id" : "gas_req"
    }
    
    pkey_a_req = {
        "jsonrpc":"2.0",
        "method":"eth_call",
        "params":[{
            "to": pow_address,
            "data": PKEY_A_SELECTOR, 
            }, "latest"],
        "id":"pkey_a_req"
    }
    
    diff_req = {
        "jsonrpc":"2.0",
        "method":"eth_call",
        "params":[{
            "to": pow_address,
            "data": DIFF_SELECTOR, 
            }, "latest"],
        "id":"diff_req"
    }
    
    return [nonce_req, gas_req, pkey_a_req, diff_req]
        
    
"""
    [DATA][STATE LOADING]
    Conduct multicall
    build params + make multicall + decode the result

    returns:
    {
        "master_nonce" : nonce of the sumbission wallet,
        "eth_feeHistory" : feeHistory for rapid tx building,
        "privateKeyA" : mining problem input,
        "difficulty" : mining problem input
    }    

"""
def get_essential_state_multicall(
        master_address,
        pow_address
    ):        
    
    multicall_params = get_essential_state_multicall_params(master_address, pow_address)
    
    result = SESSION.post(
        url = ALCHEMY_URL,
        json = multicall_params
    )
    
    if result.status_code != 200:
        return None
    
    res = json.loads(result.text)
    ret = {
        "master_nonce" : None,
        "eth_feeHistory" : None,
        "privateKeyA" : None,
        "difficulty" : None
    }    
    for sub_res in res:
        if (sub_res["id"] == "nonce_req") and ("result" in sub_res):
            ret["master_nonce"] = int(sub_res['result'], 16)
        elif (sub_res["id"] == "gas_req") and ("result" in sub_res):
            ret["eth_feeHistory"] = sub_res["result"]                
        elif (sub_res["id"] == "pkey_a_req") and ("result" in sub_res):
            ret["privateKeyA"] = sub_res["result"]
        elif (sub_res["id"] == "diff_req") and ("result" in sub_res):
            ret["difficulty"] = "0x" + sub_res["result"][26:]
        
    return ret
    

"""
    [CORE][MINER][OPENCL]

    OpenCL ~ C++ ~ python bidnings dor magic xor GPU calculus

    strPublicKey -- pub_key built on a privateKeyA from PoW.sol, hex no "0x"
    strMagicXorDifficulty -- difficulty from PoW.sol, hex no "0x"
"""
def mine_wagmi_magic_xor(
        strPublicKey,
        strMagicXorDifficulty
    ):

    result = magicXorMiner.runMagicXor(
        strPublicKey = strPublicKey,
        strMagicXorDifficulty = strMagicXorDifficulty, 
        mineContract = False, # I mean, we don't wanna mine contract, right?
        worksizeLocal = WORKSIZE_LOCAL,
        worksizeMax = WORKSIZE_MAX,
        inverseSize = INVERSE_SIZE,
        inverseMultiple = INVERSE_MULTIPLE,
        bNoCache = False, # If you want to avoid using cache, for some weird reason, you can absolutely do it here
        verboseStdOut = PROFANITY2_VERBOSE_FLAG
    )

    if "FAIL" in result:
        print("[PROFANITY2] generation failed")
        return None
    else:
        return "0x" + result
    

"""
    [UTILS][TX-BUILDER]

    Builds gas price based on the pre-fetched eth_feeHistory response!
"""
def build_gas_price(fee_history):
    base_fee_per_gas = int(fee_history['baseFeePerGas'][0], 16)
    max_priority_fee_per_gas = int(MAX_PRIORITY_FEE_MWEI * 10**6)
    max_fee_per_gas = (BASE_FEE_K * base_fee_per_gas) + max_priority_fee_per_gas
    return max_priority_fee_per_gas, max_fee_per_gas


"""
    TAKES WITH "0x"
"""
def _ensure_padding(hex_string_val):
    padd_n = 64 - len(hex_string_val[2:])
    return padd_n * "0" + hex_string_val[2:]

"""
    TAKES WITH NO!! "0x"
    needed for bytes calldata & bytes memory (continous data structures basically)
"""
def _ensure_post_padding(hex_string_val_no0x):
    padd_n = 64 - len(hex_string_val_no0x)
    return hex_string_val_no0x + padd_n * "0" 

"""
    Lt's throw the web3.py away and build the calldata manually!
    saves about 15ms!
    
    TODO
        test the signature padding consistency
        (check when signature will have zero in the begining of it)
        testes in 10M signatures --> SAFU
"""
SUBMIT_SELECTOR = "0x76fbe328"
def build_submit_tx_fast(
        master_address,
        master_nonce,
        reward_recipient_address,
        private_key_a,
        private_key_b,
        funny_data,
        fee_history
    ):
    assert(len(funny_data) <= 32) # want it bigger? do it on your own
    pub_key_x, pub_key_y = get_ecc_point(private_key_b[2:])
    private_key_ab = get_pkeys_sum(private_key_a[2:], private_key_b[2:])[2:]
    
    r, s, v = create_signature_ab(
        private_key_ab,
        reward_recipient_address,
        funny_data
    )
    
    calldata_array = [
        _ensure_padding(master_address),
        _ensure_padding(hex(pub_key_x)),
        _ensure_padding(hex(pub_key_y)),
        "00000000000000000000000000000000000000000000000000000000000000a0", # offset to signatureAB, always the same
        "0000000000000000000000000000000000000000000000000000000000000120", # offset to data, always the same
        "0000000000000000000000000000000000000000000000000000000000000041", # len of signatureAB, always the same (65 bytes)
        _ensure_padding(r), # r, 32 bytes
        _ensure_padding(s), # s, 32 bytes
        v[2:] + 62 * "0",  # v, 1 byte + 31 bytes padding
        _ensure_padding(hex(len(funny_data))), # len of the funny_data
        _ensure_post_padding(funny_data.hex()) # padded data (padding after the value)
    ]

    max_priority_fee_per_gas, max_fee_per_gas = build_gas_price(fee_history) 
    
    tx = {
        'chainId': CHAIN_ID,
        'from': master_address,
        'value': 0,
        'nonce': master_nonce,
        'gas': GAS_LIMIT_SUBMIT,
        'maxFeePerGas': max_fee_per_gas,
        'maxPriorityFeePerGas': max_priority_fee_per_gas,
        'to': POW_CONTRACT,
        'data': SUBMIT_SELECTOR + "".join(calldata_array)
    }
    
    return tx


"""
    [UTILS]
    Well, there is a bug in some versions of web3.py tx signing logic
    
    hence a fix
"""
def fix_hex(hex_n):
    if "0x" in hex_n:
        return hex_n
    else:
        return "0x" + hex_n

"""
    [TX-SIGNING]
    
    Signs the transaction, ensures consistency betweel web3.py versions

    web3.py dep here is needed for simplicity 
    & sign_transaction takes only around 0.5-2ms 
"""
def create_raw_signed_tx(tx, pkey):
    signed_tx = WEB3_IDLE_PROVIDER.eth.account.sign_transaction(tx, pkey)
    if ("raw_transaction" in signed_tx.__str__()):
        universal_signed_tx = {
            "raw_transaction" : fix_hex(signed_tx.raw_transaction.hex()),
            "tx_hash" : fix_hex(signed_tx.hash.hex())
        }
    elif ("rawTransaction" in signed_tx.__str__()):
        universal_signed_tx = {
            "raw_transaction" : fix_hex(signed_tx.rawTransaction.hex()),
            "tx_hash" : fix_hex(signed_tx.hash.hex())
        }
    return universal_signed_tx
    

"""
    [TX-BUILDING]

    Builds call payload from universal_signed_tx
"""
def signed_tx_to_call(universal_signed_tx):
    call_sample = {
        "id" : f"sent_tx_{universal_signed_tx['tx_hash']}",
        "jsonrpc" : "2.0",
        "method" : "eth_sendRawTransaction",
        "params" : [universal_signed_tx["raw_transaction"]]
    }
    return call_sample

"""
    [TX-SEND]

    Could potentialy work with multiple transactions from DIFFERENT wallets (for nonce consistency)

    raw_signed_txs -- an array of `universal_signed_tx` produced by `create_raw_signed_tx`
"""
def broadcast_signed_txs(raw_signed_txs):
    multicall_body = []
    for us_tx in raw_signed_txs:
        multicall_body.append(signed_tx_to_call(us_tx))

    response = SESSION.post(
        url = ALCHEMY_URL,
        json = multicall_body
    )

    return response



def mine_and_submit(chain_state):
    """
    Called in a separate process.  
    1) Perform GPU-based mine_wagmi_magic_xor(...)  
    2) Submit transaction.  
    """
    try:
        if (MINER_VERBOSE_FLAG):
            print(f"[MINER][{time.time():.3f}] STARTED for pkeyA: {chain_state['privateKeyA']}")

        private_key_b = mine_wagmi_magic_xor(
            strPublicKey = get_secp256k1_pub(chain_state["privateKeyA"][2:]),
            strMagicXorDifficulty = chain_state["difficulty"][2:]
        )

        if (MINER_VERBOSE_FLAG):
            print(f"[MINER][{time.time():.3f}] Obtained privateKeyB: {private_key_b}")

        # submit the result
        tx = build_submit_tx_fast(
            master_address = MASTER_ADDRESS,
            master_nonce = chain_state["master_nonce"],
            reward_recipient_address = REWARDS_RECIPIENT_ADDRESS,
            private_key_a = chain_state["privateKeyA"],
            private_key_b = private_key_b,
            funny_data = SIGN_DATA,
            fee_history = chain_state["eth_feeHistory"]
        )
        
        signed_tx = create_raw_signed_tx(tx, MASTER_PKEY)

        if (MINER_VERBOSE_FLAG):
            print(f"[MINER][{time.time():.3f}] build and signed tx with tx_hash: {signed_tx['tx_hash']}")

        broadcast_signed_txs([signed_tx])
        if (MINER_VERBOSE_FLAG):
            print(f"[MINER][{time.time():.3f}] BROADCASTED")
            print()

    except Exception as e:
        print("[MINER] Exception in miner process:", e)


"""
    WebSockets event listener for new problem 

    POW_NEW_PROBLEM_TOPIC0
"""
def websocket_listener(ws_url: str):
    def on_message(ws, message):
        print("[WS] Received message:", message)

        new_params = {
            "privateKeyA"    : "0x123abc...",     # example
            "difficulty"     : "0x0000fffff...", 
            "master_nonce"   : 42,
            "eth_feeHistory" : {...}               # or however you retrieve it
        }
        event_queue.put(new_params)

    def on_error(ws, error):
        print("[WS] Error:", error)

    def on_close(ws, close_status_code, close_msg):
        print("[WS] Closed:", close_status_code, close_msg)

    def on_open(ws):
        print("[WS] Connection opened to", ws_url)
        # You might send subscription params, e.g. filter logs, etc.

    ws = websocket.WebSocketApp(
        ws_url,
        on_open=on_open,
        on_message=on_message,
        on_error=on_error,
        on_close=on_close
    )
    # This call will block forever in this thread, reading messages:
    ws.run_forever()


"""
    Alright, this one seems to work better

    1) fix polling timings

    2) add websockets

    3) check how long it actually takes to stop mining and whether we shall start new process immediately and do a cleanup later


    Alright:
    current_miner_process.terminate()
    current_miner_process.join()

    + relaunch the process takes only arounf 6-9ms, so we are good
"""
def main_loop():

    global current_miner_process, last_privateKeyA

    while True:
        if (MINER_VERBOSE_FLAG):
            print(f"[DATA-LOADER][{time.time():.3f}] Preparing for State Loading")
        chain_state = get_essential_state_multicall(
            master_address = MASTER_ADDRESS,
            pow_address = POW_CONTRACT
        )

        # quick patch for testing only!
        chain_state["difficulty"] = "0x000000ffffffffffffffffffffffffffffffffff"

        if (MINER_VERBOSE_FLAG):
            print(f"[DATA-LOADER][{time.time():.3f}] Obtained State:")
            print(f"[DATA-LOADER] master_nonce: {chain_state['master_nonce']}")
            print(f"[DATA-LOADER] privateKeyA: {chain_state['privateKeyA']}")
            print(f"[DATA-LOADER] difficulty: {chain_state['difficulty']}")
            print()

        new_pkA = chain_state["privateKeyA"]
        if new_pkA and new_pkA != last_privateKeyA:
            if (MINER_VERBOSE_FLAG):
                print(f"[DATA-LOADER][{time.time():.3f}] Detected new privateKeyA, starting MINER.")

            if current_miner_process and current_miner_process.is_alive():
                if (MINER_VERBOSE_FLAG):
                    print(f"[DATA-LOADER][{time.time():.3f}] killing old miner")
                current_miner_process.terminate()
                current_miner_process.join()
                current_miner_process = None
                if (MINER_VERBOSE_FLAG):
                    print(f"[DATA-LOADER][{time.time():.3f}] KILLED")

            current_miner_process = multiprocessing.Process(
                target=mine_and_submit,
                args=(chain_state,),
            )
            current_miner_process.start()
            print(f"[DATA-LOADER][{time.time():.3f}] Spawned new miner")

            last_privateKeyA = new_pkA

        # adjust timing logic
        time.sleep(1)



if __name__ == "__main__":
    main_loop()


