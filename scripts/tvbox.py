#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import binascii
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad


# ============================================================
# 工具函数
# ============================================================

def utf8_to_hex(s: str) -> str:
    return binascii.hexlify(s.encode("utf-8")).decode("utf-8")


def hex_to_utf8(h: str) -> str:
    return bytes.fromhex(h).decode("utf-8")


def aes_encrypt(data: str, key: str, iv: str) -> str:
    key = key.ljust(16, "0").encode("utf-8")
    iv = iv.ljust(16, "0").encode("utf-8")

    cipher = AES.new(key, AES.MODE_CBC, iv)
    encrypted = cipher.encrypt(pad(data.encode("utf-8"), AES.block_size))
    return binascii.hexlify(encrypted).decode("utf-8")


def aes_decrypt(cipher_hex: str, key: str, iv: str) -> str:
    key = key.ljust(16, "0").encode("utf-8")
    iv = iv.ljust(16, "0").encode("utf-8")

    cipher = AES.new(key, AES.MODE_CBC, iv)
    decrypted = cipher.decrypt(bytes.fromhex(cipher_hex))
    try:
        return unpad(decrypted, AES.block_size).decode("utf-8")
    except Exception:
        return decrypted.decode("utf-8", errors="ignore")


# ============================================================
# 完整版影视仓解密（支持所有格式）
# ============================================================

def decrypt_full(encrypted_hex: str) -> str:
    encrypted_hex = encrypted_hex.strip()

    # "$#" → hex
    prefix_hex = utf8_to_hex("$#")  # "2423"
    suffix_hex = utf8_to_hex("#$")  # "2324"

    # 找到 keyHex 的结束位置
    idx_suffix = encrypted_hex.find(suffix_hex)
    if idx_suffix == -1:
        raise ValueError("未找到 key 尾标记 '#$' 的 Hex")

    pwd_mix = encrypted_hex[:idx_suffix + len(suffix_hex)]

    # 最后 26 个 hex 是 ivHex
    roundtime_hex = encrypted_hex[-26:]
    encrypted_text_hex = encrypted_hex[len(pwd_mix):-26]

    # 去掉 "$#" 和 "#$"
    pwd_hex = pwd_mix[len(prefix_hex):len(pwd_mix) - len(suffix_hex)]

    # Hex → 字符串
    pwd = hex_to_utf8(pwd_hex)
    round_time = hex_to_utf8(roundtime_hex)

    # 补齐到 16 字节
    key = pwd.ljust(16, "0")
    iv = round_time.ljust(16, "0")

    # AES 解密
    return aes_decrypt(encrypted_text_hex, key, iv)


# ============================================================
# 完整版影视仓加密（支持自定义 key/iv）
# ============================================================

def encrypt_full(data: str, key: str, iv: str) -> str:
    key_hex = utf8_to_hex(f"$#{key}#$")
    iv_hex = utf8_to_hex(iv)

    cipher_hex = aes_encrypt(data, key, iv)

    return key_hex + cipher_hex + iv_hex


# ============================================================
# 自动识别并解密（兼容旧 tvbox.py）
# ============================================================

def decrypt_auto(cipher: str) -> str:
    cipher = cipher.strip()

    # 如果是纯 hex 串并且包含 "$#" 和 "#$" 的 hex → 完整版协议
    if all(c in "0123456789abcdefABCDEF" for c in cipher):
        if utf8_to_hex("$#") in cipher and utf8_to_hex("#$") in cipher:
            return decrypt_full(cipher)

    # 否则走旧 tvbox.py 的逻辑（你可以自己补）
    raise ValueError("无法识别的加密格式，请使用完整版协议。")


# ============================================================
# 主入口
# ============================================================

if __name__ == "__main__":
    import sys

    if len(sys.argv) < 4:
        print("用法：python tvbox_full.py enc|dec 输入文件 输出文件 [key] [iv]")
        sys.exit(1)

    mode = sys.argv[1]
    infile = sys.argv[2]
    outfile = sys.argv[3]

    key = sys.argv[4] if len(sys.argv) > 4 else "KenKey2026"
    iv = sys.argv[5] if len(sys.argv) > 5 else "KenIV2026"

    with open(infile, "r", encoding="utf-8") as f:
        content = f.read()

    if mode == "enc":
        result = encrypt_full(content, key, iv)
    elif mode == "dec":
        result = decrypt_auto(content)
    else:
        print("模式必须是 enc 或 dec")
        sys.exit(1)

    with open(outfile, "w", encoding="utf-8") as f:
        f.write(result)

    print(f"完成：{outfile}")
