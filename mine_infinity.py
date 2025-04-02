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
import math
from dotenv import load_dotenv
import os

"""
    TODO:
        Simpler installation guide

        explain more .env logic 
        AND create simple wallet create & walkthough
"""

"""
    VALUABLES!!!
"""
load_dotenv() 
# you could optionally choose a different address for the rewards
MASTER_ADDRESS = os.getenv("MASTER_ADDRESS")
MASTER_PKEY = os.getenv("MASTER_PKEY")
REWARDS_RECIPIENT_ADDRESS = os.getenv("REWARDS_RECIPIENT_ADDRESS")

"""
    CONFIG & TUNING
"""

# chain specific details
INFINITY_RPC = os.getenv("INFINITY_RPC") 
INFINITY_WS = os.getenv("INFINITY_WS") 

CHAIN_ID = 57054

POW_CONTRACT = "0x8888FF459Da48e5c9883f893fc8653c8E55F8888"
POW_NEW_PROBLEM_TOPIC0 = "0xa100d84256eafde4f67167e266005a7b734f135b1ba16dd349e2469a81d05c47"
PROBLEM_SELECTOR = "0x88f116d0"
GAS_LIMIT_SUBMIT = 2_000_000

# be creative, pick your own data, don't make it too long though,
# code will compulsory fail if len(SIGN_DATA) > 32
# so, keep that in mind
SIGN_DATA = bytes.fromhex("deadbeef1337cafebabe")

# [TX-BUILDER] feel free to tune it
MAX_PRIORITY_FEE_MWEI = 500
BASE_FEE_K = 2

# [MINER] Mining params section:
# feel free to tweak this parameters until it works the best for you
# original profanity2 params are mirrored here: https://github.com/1inch/profanity2
"""
TOONING 

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
MINER_VERBOSE_FLAG = True # don't toggle these both to True -- they will mix, one at a time please



PROBLEMS_QUEUE = queue.Queue()
POLL_RESULTS_QUEUE = queue.Queue()
WEB3_IDLE_PROVIDER = Web3()
SESSION = requests.Session()



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


def _parse_promlem_req(data):
    if "0x" in data:
        data = data[2:]
    nonce = int("0x" + data[0 : 64], 16)
    privateKeyA = "0x" + data[64 : 128]
    diff = "0x" + data[128 + 24 :]
    return nonce, privateKeyA, diff
            
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
    
    problem_req = {
        "jsonrpc":"2.0",
        "method":"eth_call",
        "params":[{
            "to": pow_address,
            "data": PROBLEM_SELECTOR, 
            }, "latest"],
        "id":"problem_req"
    }
        
    result = SESSION.post(
        url = INFINITY_RPC,
        json = [nonce_req, gas_req, problem_req]
    )
    
    if result.status_code != 200:
        return None
    
    res = json.loads(result.text)
    ret = {
        "master_nonce" : None,
        "eth_feeHistory" : None,
        "privateKeyA" : None,
        "difficulty" : None,
        "problemNonce" : None
    }   
    
    for sub_res in res:
        if (sub_res["id"] == "nonce_req") and ("result" in sub_res):
            ret["master_nonce"] = int(sub_res['result'], 16)
        elif (sub_res["id"] == "gas_req") and ("result" in sub_res):
            ret["eth_feeHistory"] = sub_res["result"]                
        elif (sub_res["id"] == "problem_req") and ("result" in sub_res):
            nonce, pkey, diff = _parse_promlem_req(sub_res["result"])
            ret["privateKeyA"] = pkey
            ret["difficulty"] = diff
            ret["problemNonce"] = nonce
        
    if (ret["master_nonce"] == None) or (ret["eth_feeHistory"] == None) or (ret["privateKeyA"] == None) or (ret["difficulty"] == None) or (ret["problemNonce"] == None):
        return None
    else:
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
        url = INFINITY_RPC,
        json = multicall_body
    )

    return response



def mine_and_submit(el_problemo, chain_data_latest):
    """
    Called in a separate process.  
    1) Perform GPU-based mine_wagmi_magic_xor(...)  
    2) Submit transaction.  
    """
    try:
        if (MINER_VERBOSE_FLAG):
            print(f"[MINER][{time.time():.3f}] STARTED for pkeyA: {el_problemo['privateKeyA']}")

        private_key_b = mine_wagmi_magic_xor(
            strPublicKey = get_secp256k1_pub(el_problemo["privateKeyA"][2:]),
            strMagicXorDifficulty = el_problemo["difficulty"][2:]
        )

        if (MINER_VERBOSE_FLAG):
            print(f"[MINER][{time.time():.3f}] Obtained privateKeyB: {private_key_b}")

        # submit the result
        tx = build_submit_tx_fast(
            master_address = MASTER_ADDRESS,
            master_nonce = chain_data_latest["master_nonce"],
            reward_recipient_address = REWARDS_RECIPIENT_ADDRESS,
            private_key_a = el_problemo["privateKeyA"],
            private_key_b = private_key_b,
            funny_data = SIGN_DATA,
            fee_history = chain_data_latest["eth_feeHistory"]
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
    [WS-LISTENER]

    Just listens for new events
    decodes 
    and puts them in a queue
"""
def listen_for_problems(ws_url, contract_address, event_topic):
    ws = create_connection(ws_url)
    subscription_request = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "eth_subscribe",
        "params": [
            "logs",
            {
                "address": contract_address,
                "topics": [event_topic]
            },
        ],
    }
    ws.send(json.dumps(subscription_request))

    sub_reply = ws.recv()
    if (True):
        print(f"[WS-LISTENER][{time.time():.3f}] Subscribed. Reply: {sub_reply}")

    while True:
        raw_message = ws.recv() 
        data = json.loads(raw_message)

        if "params" not in data or "result" not in data["params"]:
            continue 

        log_result = data["params"]["result"]
        if "data" not in log_result:
            continue  

        problem_data_hex = log_result["data"] 
        problem_data_n0x = problem_data_hex[2:]

        decoded_vals = decode(["uint256","uint256","uint160"], bytes.fromhex(problem_data_n0x))
        problem_nonce, pkey_A, difficulty_uint = decoded_vals

        difficulty_hex = "0x" + format(difficulty_uint, "040x")
        privateKeyA_hex = "0x" + format(pkey_A, "x")

        if (MINER_VERBOSE_FLAG):
            print(f"[WS-LISTENER][{time.time():.3f}] NewProblem Detected")
            print(f"[WS-LISTENER] difficulty: {difficulty_hex}")
            print(f"[WS-LISTENER] privateKeyA_hex: {privateKeyA_hex}")
            print(f"[WS-LISTENER] problemNonce: {problem_nonce}")
            print()

        new_problem = {
            "difficulty": difficulty_hex,
            "privateKeyA": privateKeyA_hex,
            "problemNonce" : problem_nonce
        }
        PROBLEMS_QUEUE.put(new_problem)


"""
    [UTILS]
     A small helper to sleep until the next multiple of `step_s` seconds
"""
def sleep_to_next_multiple(step_s):
    t_now = time.time()
    next_t = math.ceil(t_now / step_s) * step_s
    time.sleep(max(0, next_t - t_now))

"""
    [STATE-LOADER]
"""
def poll_state_periodically(poll_interval=0.5):
    while True:
        try:
            if (MINER_VERBOSE_FLAG):
                print(f"[POLLING][{time.time():.3f}] Preparing for polling step")

            polled_data = get_essential_state_multicall(
                master_address = MASTER_ADDRESS,
                pow_address = POW_CONTRACT
            )

            if (MINER_VERBOSE_FLAG):
                print(f"[POLLING[{time.time():.3f}] Obtained State:")
                print(f"[POLLING] master_nonce: {polled_data['master_nonce']}")
                print(f"[POLLING] privateKeyA: {polled_data['privateKeyA']}")
                print(f"[POLLING] difficulty: {polled_data['difficulty']}")
                print(f"[POLLING] problemNonce: {polled_data['problemNonce']}")
                print()

            if polled_data and polled_data["master_nonce"] != None:
                POLL_RESULTS_QUEUE.put(polled_data) 
        except Exception as e:
            print("[POLLING] Exception during polling:", e)

        sleep_to_next_multiple(poll_interval)


"""
    Main Loop
    Every 5ms:
    1) checks polling updates 
    2) checks ws updates
    3) launches / restarts miner on new task

    all in non-blocking manner

    latest nonce & eth_feeHistory are passed to mine_and_submit through the multiprocessing.Manager()

    TODO:
        Consired restarting logic if miner is dead
"""
def main_loop():

    manager = multiprocessing.Manager()
    chain_data_latest = manager.dict()
    chain_data_latest["master_nonce"] = 0
    chain_data_latest["eth_feeHistory"] = {}

    current_miner_process = None
    last_poll_data = None 
    last_problem = None
    pkey_in_work = None
    actually_latest_pkey = None

    if (MINER_VERBOSE_FLAG):
        print(f"[MAIN-LOOP][{time.time():.3f}] STARTING")

    while True:
        while not POLL_RESULTS_QUEUE.empty():
            last_poll_data = POLL_RESULTS_QUEUE.get()

            # bootstrap last_problem on launch
            if ((last_poll_data != None) and (last_problem == None)):
                last_problem = { 
                    "difficulty" : last_poll_data["difficulty"], 
                    "privateKeyA" : last_poll_data["privateKeyA"],
                    "problemNonce" : last_poll_data["problemNonce"]
                }

            if (MINER_VERBOSE_FLAG):
                print(f"[MAIN-LOOP][{time.time():.3f}] got polling update")

            # submit part in mine_and_submit will take the latest state from here
            chain_data_latest["master_nonce"] = last_poll_data["master_nonce"]
            chain_data_latest["eth_feeHistory"] = last_poll_data["eth_feeHistory"]

        while not PROBLEMS_QUEUE.empty():
            last_problem = PROBLEMS_QUEUE.get() 
            if (MINER_VERBOSE_FLAG):
                print(f"[MAIN-LOOP][{time.time():.3f}] got websockets update")

        """
            Safety check for situations where:
            1) polling ended up being faster that ws
            2) ws data packet has been lost

            polling is somewhat more reliable yet slow

            we could change this logic to make it problemNonce based
        """
        if ((last_poll_data and last_problem)):
            actually_latest_pkey = last_problem["privateKeyA"]
            if (last_problem["privateKeyA"] != last_poll_data["privateKeyA"]):
                if (last_poll_data["privateKeyA"] != pkey_in_work):
                    actually_latest_pkey = last_poll_data["privateKeyA"]
                    last_problem["privateKeyA"] = last_poll_data["privateKeyA"]
                else:
                    last_poll_data["privateKeyA"] = last_problem["privateKeyA"]

        """
            Check on our mate - miner
        """
        if current_miner_process and not current_miner_process.is_alive():
            pkey_in_work = None  
            if MINER_VERBOSE_FLAG:
                print(f"[MAIN-LOOP][{time.time():.3f}] MINER BROSKIII HAS DIEEDDD")

        if ((last_poll_data and last_problem) and (actually_latest_pkey != pkey_in_work)):
            if (MINER_VERBOSE_FLAG):
                print(f"[MAIN-LOOP][{time.time():.3f}] new problem detected - relaunching MINER")
                print(f"[MAIN-LOOP] diff: {last_problem['difficulty']}")
                print(f"[MAIN-LOOP] pkey: {actually_latest_pkey}")
                print(f"[MAIN-LOOP] problemNonce: {last_problem['problemNonce']}")

            el_problemo = {
                "privateKeyA":    actually_latest_pkey,
                "difficulty":     last_problem["difficulty"]
            }

            if current_miner_process and current_miner_process.is_alive():
                current_miner_process.terminate()
                current_miner_process.join()
                if MINER_VERBOSE_FLAG:
                    print(f"[MAIN-LOOP][{time.time():.3f}] KILLED OLD MINER")

            current_miner_process = multiprocessing.Process(
                target=mine_and_submit,
                args=(el_problemo, chain_data_latest),
            )
            current_miner_process.start()

            if MINER_VERBOSE_FLAG:
                print(f"[MAIN-LOOP][{time.time():.3f}] SPAWNED NEW MINER")

            pkey_in_work = actually_latest_pkey

        sleep_to_next_multiple(0.005)
        

"""
    Launch:
    1) websockets thread
    2) polling thread
    3) main loop managing them all (and launching miner)
"""
if __name__ == "__main__":
    ws_thread = threading.Thread(
        target=listen_for_problems,
        args=(INFINITY_WS, POW_CONTRACT, POW_NEW_PROBLEM_TOPIC0),
        daemon=True
    )
    ws_thread.start()

    poll_thread = threading.Thread(
        target=poll_state_periodically,
        args=(0.5,),  # poll every 0.5s
        daemon=True
    )
    poll_thread.start()

    main_loop()


