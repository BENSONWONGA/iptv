#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""宝塔面板登录客户端（Odoo 20 部署前置）
用法: python3 bt_login.py            # 测试登录
      python3 bt_login.py cmd "ls"   # 后续扩展
"""
import base64
import hashlib
import json
import re
import sys

import requests
from Crypto.Cipher import PKCS1_v1_5
from Crypto.PublicKey import RSA

BT_URL = 'http://220.162.99.166:8900'
SAFE_ENTRY = '/benson'
BT_USER = 'benson'
BT_PASS = 'benson'
UA = ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
      '(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36')


def md5(s):
    return hashlib.md5(s.encode('utf-8')).hexdigest()


def normalize_pem(pem):
    pem = pem.strip()
    pem = pem.replace('\r', '').replace('\n', '')
    pem = pem.replace('-----BEGIN PUBLIC KEY-----', '-----BEGIN PUBLIC KEY-----\n')
    pem = pem.replace('-----END PUBLIC KEY-----', '\n-----END PUBLIC KEY-----')
    # 每 64 字符插入换行
    lines = pem.split('\n')
    if len(lines) == 3:  # BEGIN / body / END
        body = lines[1]
        lines[1] = '\n'.join(body[i:i + 64] for i in range(0, len(body), 64))
        pem = '\n'.join(lines)
    return pem


def rsa_encrypt(pubkey_pem, plaintext):
    key = RSA.import_key(normalize_pem(pubkey_pem))
    cipher = PKCS1_v1_5.new(key)
    ct = cipher.encrypt(plaintext.encode('utf-8'))
    return base64.b64encode(ct).decode()


class BTClient:

    def __init__(self):
        self.s = requests.Session()
        self.s.headers.update({'User-Agent': UA})
        self.s.proxies = {'http': 'http://127.0.0.1:18080',
                          'https': 'http://127.0.0.1:18080'}

    def get_login_page(self):
        """访问安全入口，拿 RSA 公钥 + login_token + cookie"""
        r = self.s.get(BT_URL + SAFE_ENTRY, timeout=15)
        r.raise_for_status()
        html = r.text
        token = re.search(r"vite_public_login_token\s*=\s*'([^']+)'", html)
        pubkey = re.search(r"vite_public_encryption\s*=\s*'([^']+)'", html)
        if not token or not pubkey:
            raise RuntimeError('无法从登录页提取 token/公钥 (页面 %d 字节)' % len(html))
        return token.group(1), pubkey.group(1)

    def login(self):
        token, pubkey = self.get_login_page()
        print('login_token:', token)
        # JS 逻辑: username = RSA(md5(md5(user + login_token)))
        #          password = RSA(md5( md5(pwd) + "_bt.cn" ))   ← 注意拼接顺序
        user_enc = rsa_encrypt(pubkey, md5(md5(BT_USER + token)))
        pass_enc = rsa_encrypt(pubkey, md5(md5(BT_PASS) + '_bt.cn'))
        r = self.s.post(BT_URL + '/login',
                        data={'username': user_enc, 'password': pass_enc},
                        timeout=15)
        print('HTTP', r.status_code)
        try:
            data = r.json()
        except Exception:
            data = r.text[:300]
        print('响应:', json.dumps(data, ensure_ascii=False) if not isinstance(data, str) else data)
        if isinstance(data, dict) and data.get('status'):
            print('=== 登录成功 ===')
            return True
        return False

    def post(self, path, data=None):
        r = self.s.post(BT_URL + path, data=data or {}, timeout=30)
        try:
            return r.json()
        except Exception:
            return {'_raw': r.text[:500], '_code': r.status_code}


if __name__ == '__main__':
    c = BTClient()
    ok = c.login()
    sys.exit(0 if ok else 1)
