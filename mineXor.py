from ecdsa import SigningKey, SECP256k1
import magicXorMiner
import sha3 # pip install safe-pysha3


"""
    ToDo list:
    1) ideally -- omit profanity2 text output

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



PKEY = "f5b4156dd24b33c961a681c747ef979d98d13e373061b123c7062ce9f2574a38"
DIFF = "000000ffffffffffffffffffffffffffffffffff"

def main():
    pub = get_secp256k1_pub(PKEY)

    pkey_generated = mine_wagmi_magic_xor(
        strPublicKey = pub,
        strMagicXorDifficulty = DIFF
    )

    if "FAIL" in pkey_generated:
        print("[PROFANITY2] generation failed")
        return None

    pkey_a = int("0x" + PKEY, 16)
    pkey_b = int("0x" + pkey_generated, 16)
    pkey_full = hex((pkey_a + pkey_b) % 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEFFFFFC2F)

    print(pkey_full)

    print(get_secp256k1_pub(pkey_full[2:]))



if __name__ == "__main__":
    main()