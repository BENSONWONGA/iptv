#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""通过宝塔执行通道重置 Odoo admin 密码"""
import base64

from bt_exec import BTExec

NEW_PASS = 'Benson@2026'

PY = f'''
from passlib.hash import pbkdf2_sha512
import psycopg2
h = pbkdf2_sha512.using(rounds=600000).hash('{NEW_PASS}')
conn = psycopg2.connect(host='127.0.0.1', port=5432, user='odoo20', password='Odoo20db_Qk7mVz2L', dbname='benson')
cur = conn.cursor()
cur.execute("update res_users set password=%s where id=2", (h,))
conn.commit()
print('updated rows:', cur.rowcount)
print('hash head:', h[:30])
'''

b64 = base64.b64encode(PY.encode()).decode()
cmd = "echo %s | base64 -d > /tmp/rst.py && /opt/odoo20/venv/bin/python3 /tmp/rst.py && rm -f /tmp/rst.py" % b64

ex = BTExec()
out = ex.run(cmd, timeout=30)
print(out)
