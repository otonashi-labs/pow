from ecdsa import SigningKey, SECP256k1
import magicXorMiner
import sha3 # pip install safe-pysha3


"""
    Alright, the mighty GPU part is officialy done. 
    It could run both on mac os 

    AND on GPUs
    AND EVEN ON CLUSTERS

    time to build the data pipeline
    
    1) load state
    2) mine
    3) submit

    ideally, while mining we will need to listen or pull for state update 
    and on state update -- re-initialize mining 

    Lets start with naive web3 aprooach 

    which later will be replaced woth somewhat optimized multicalls!

"""


"""
    private_key_hex -- str no "0x"
"""
def get_address_from_pkey(private_key_hex):
    private_key_bytes = bytes.fromhex(private_key_hex)
    sk = SigningKey.from_string(private_key_bytes, curve=SECP256k1)
    vk = sk.get_verifying_key()
    public_key_bytes = vk.to_string()
    k = sha3.keccak_256()
    k.update(public_key_bytes)
    address_bytes = k.digest()[-20:]
    address = "0x" + address_bytes.hex()
    return address


"""
    private_key_hex -- hex no '0x'
"""
def get_secp256k1_pub(private_key_hex):
    sk = SigningKey.from_string(string = bytes.fromhex(private_key_hex), curve=SECP256k1)
    vk = sk.verifying_key
    public_key_bytes = vk.to_string()
    public_key_hex = public_key_bytes.hex()
    return public_key_hex


def mine_wagmi_magic_xor(
        strPublicKey,
        strMagicXorDifficulty
    ):

    result = magicXorMiner.runMagicXor(
        strPublicKey = strPublicKey,
        strMagicXorDifficulty = strMagicXorDifficulty, 
        mineContract = False,
        worksizeLocal = 64,
        worksizeMax = 0,
        inverseSize = 255,
        inverseMultiple = 1024,
        bNoCache = False,
        verboseStdOut = True
    )

    return result


def _pkey_paddding_hex(uint256_hex):
    numba = uint256_hex[2:]
    padd_n = 64 - len(numba)
    return "0x" + padd_n * "0" + numba

def get_pkeys_sum(pkey_a_hex, pkey_b_hex):
    pkey_a = int("0x" + pkey_a_hex, 16)
    pkey_b = int("0x" + pkey_b_hex, 16)
    pkey_full = hex((pkey_a + pkey_b) % 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEFFFFFC2F)
    return _pkey_paddding_hex(pkey_full)


PKEY = "4e88558d1e3f6e1a56c6d44bca7489b0df4a8a19a43de2c3ba478fc425a317cd"
DIFF = "00000fffffffffffffffffffffffffffffffffff"

def main():
    pub = get_secp256k1_pub(PKEY)

    pkey_generated = mine_wagmi_magic_xor(
        strPublicKey = pub,
        strMagicXorDifficulty = DIFF
    )

    if "FAIL" in pkey_generated:
        print("[PROFANITY2] generation failed")
        return None

    pkey_full = get_pkeys_sum(PKEY, pkey_generated)

    print(pkey_full)
    print(get_secp256k1_pub(pkey_full[2:]))



if __name__ == "__main__":
    main()