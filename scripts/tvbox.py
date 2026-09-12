import json
import binascii
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad


def is_hex(s: str) -> bool:
    return all(c in "0123456789abcdefABCDEF" for c in s)


def is_json(s: str) -> bool:
    try:
        json.loads(s)
        return True
    except:
        return False


def decrypt_full(cipher_hex: str) -> str:
    prefix_hex = binascii.hexlify("$#".encode()).decode()  # 2423
    suffix_hex = binascii.hexlify("#$".encode()).decode()  # 2324

    idx_suffix = cipher_hex.find(suffix_hex)
    pwd_mix = cipher_hex[:idx_suffix + len(suffix_hex)]

    roundtime_hex = cipher_hex[-26:]
    encrypted_text_hex = cipher_hex[len(pwd_mix):-26]

    pwd_hex = pwd_mix[len(prefix_hex):len(pwd_mix) - len(suffix_hex)]

    pwd = bytes.fromhex(pwd_hex).decode()
    round_time = bytes.fromhex(roundtime_hex).decode()

    key = pwd.ljust(16, "0").encode()
    iv = round_time.ljust(16, "0").encode()

    cipher = AES.new(key, AES.MODE_CBC, iv)
    decrypted = cipher.decrypt(bytes.fromhex(encrypted_text_hex))

    pad_len = decrypted[-1]
    return decrypted[:-pad_len].decode("utf-8", errors="ignore")


def encrypt_full(data: str, key="KenKey2026", iv="KenIV2026") -> str:
    key_hex = binascii.hexlify(f"$#{key}#$".encode()).decode()
    iv_hex = binascii.hexlify(iv.encode()).decode()

    key_bytes = key.ljust(16, "0").encode()
    iv_bytes = iv.ljust(16, "0").encode()

    cipher = AES.new(key_bytes, AES.MODE_CBC, iv_bytes)
    encrypted = cipher.encrypt(pad(data.encode(), AES.block_size))
    cipher_hex = binascii.hexlify(encrypted).decode()

    return key_hex + cipher_hex + iv_hex


def auto_mode(infile: str, outfile: str):
    with open(infile, "r", encoding="utf-8") as f:
        content = f.read().strip()

    # 自动识别 JSON → 加密
    if is_json(content):
        result = encrypt_full(content)
        with open(outfile, "w", encoding="utf-8") as f:
            f.write(result)
        print("自动识别：明文 JSON → 已加密")
        return

    # 自动识别影视仓密文 → 解密
    if is_hex(content) and "2423" in content and "2324" in content:
        result = decrypt_full(content)
        with open(outfile, "w", encoding="utf-8") as f:
            f.write(result)
        print("自动识别：影视仓密文 → 已解密")
        return

    raise ValueError("无法识别输入文件格式，既不是 JSON，也不是影视仓密文。")


if __name__ == "__main__":
    import sys
    if len(sys.argv) != 3:
        print("用法：python tvbox.py 输入文件 输出文件")
        sys.exit(1)

    auto_mode(sys.argv[1], sys.argv[2])
