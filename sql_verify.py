#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""验证库连接与 quant 全貌"""
from bt_exec import BTExec

ex = BTExec()
out = ex.run(
    "sudo -u postgres psql benson -c \"SELECT count(*) AS quant_rows FROM stock_quant; "
    "SELECT count(*) AS done_moves FROM stock_move WHERE state='done'; "
    "SELECT count(*) AS mos FROM mrp_production; "
    "SELECT id, quantity, reserved_quantity, location_id FROM stock_quant WHERE product_id=58;\"",
    timeout=60, name='sql-verify')
print(out)
