#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import binascii
import sys
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad


# ============================================================
# 工具函数
# ============================================================

def is_hex(s: str) -> bool:
    return all(c in "0123456789abcdefABCDEF" for c in s)


def is_json(s: str) -> bool:
    try:
        json.loads(s)
        return True
    except:
        return False


def try_pretty_json(text: str) -> str:
    try:
        obj = json.loads(text)
        return json.dumps(obj, ensure_ascii=False, indent=2)
    except:
        return text


# ============================================================
# 完整影视仓解密
# ============================================================

def decrypt_full(cipher_hex: str) -> str:
    cipher_hex = cipher_hex.strip()

    prefix_hex = binascii.hexlify("$#".encode()).decode()  # "2423"
    suffix_hex = binascii.hexlify("#$".encode()).decode()  # "2324"

    idx_suffix = cipher_hex.find(suffix_hex)
    if idx_suffix == -1:
        raise ValueError("未找到 key 尾标记 '#$' 的 Hex")

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


# ============================================================
# 完整影视仓加密
# ============================================================

def encrypt_full(data: str, key="KenKey2026", iv="2024010100000"):
    """
    影视仓协议加密（与 decrypt_full 完全对称）
    """
    # 1. keyHex = hex("$#"+key+"#$")
    key_hex = binascii.hexlify(f"$#{key}#$".encode()).decode()
    # 2. ivHex = hex(iv)  ← iv 必须是 13 字节，否则影视仓不认
    iv_hex = binascii.hexlify(iv.encode()).decode()
    if len(iv_hex) != 26:
        raise ValueError("影视仓协议要求 iv 必须是 13 字节（hex 长度 26）")
    # 3. AES-CBC 加密（影视仓要求 key/iv 补齐到 16 字节）
    key_bytes = key.ljust(16, "0").encode()
    iv_bytes = iv.ljust(16, "0").encode()
    cipher = AES.new(key_bytes, AES.MODE_CBC, iv_bytes)
    encrypted = cipher.encrypt(pad(data.encode(), AES.block_size))
    cipher_hex = binascii.hexlify(encrypted).decode()
    # 4. 拼接成最终协议格式
    return key_hex + cipher_hex + iv_hex



# ============================================================
# 自动识别模式（用于手动运行）
# ============================================================

def auto_mode(infile: str, outfile: str):
    with open(infile, "r", encoding="utf-8") as f:
        content = f.read().strip()

    # JSON → 自动加密
    if is_json(content):
        result = encrypt_full(content)
        with open(outfile, "w", encoding="utf-8") as f:
            f.write(result)
        print("自动识别：明文 JSON → 已加密")
        return

    # 影视仓密文 → 自动解密
    if is_hex(content) and "2423" in content and "2324" in content:
        result = decrypt_full(content)
        result = try_pretty_json(result)
        with open(outfile, "w", encoding="utf-8") as f:
            f.write(result)
        print("自动识别：影视仓密文 → 已解密并格式化 JSON")
        return

    raise ValueError("无法识别输入文件格式")


# ============================================================
# 主入口（兼容 enc/dec + 自动识别）
# ============================================================

if __name__ == "__main__":
    args = sys.argv

    # 兼容旧版：python tvbox.py infile outfile enc
    if len(args) == 4 and args[3] in ("enc", "dec"):
        infile, outfile, mode = args[1], args[2], args[3]

    # 兼容新版：python tvbox.py enc infile outfile
    elif len(args) == 4 and args[1] in ("enc", "dec"):
        mode, infile, outfile = args[1], args[2], args[3]

    # 自动识别模式：python tvbox.py infile outfile
    elif len(args) == 3:
        auto_mode(args[1], args[2])
        sys.exit(0)

    else:
        print("用法：")
        print("  自动识别模式：python tvbox.py 输入 输出")
        print("  旧版兼容：    python tvbox.py 输入 输出 enc|dec")
        print("  新版兼容：    python tvbox.py enc|dec 输入 输出")
        sys.exit(1)

    # 执行 enc/dec 模式
    with open(infile, "r", encoding="utf-8") as f:
        content = f.read().strip()

    if mode == "enc":
        result = encrypt_full(content)
    else:
        result = decrypt_full(content)
        result = try_pretty_json(result)

    with open(outfile, "w", encoding="utf-8") as f:
        f.write(result)

    print(f"完成：{mode} → {outfile}")
