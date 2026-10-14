#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""单查 count"""
from bt_exec import BTExec

ex = BTExec()
out = ex.run(
    "sudo -u postgres psql benson -t -c \"SELECT 'quant_rows=' || count(*) FROM stock_quant;\" "
    "-c \"SELECT 'done_moves=' || count(*) FROM stock_move WHERE state='done';\" "
    "-c \"SELECT 'mos=' || count(*) FROM mrp_production;\" "
    "-c \"SELECT 'q58=' || count(*) FROM stock_quant WHERE product_id=58;\" "
    "-c \"SELECT 'mv58=' || count(*) FROM stock_move WHERE product_id=58 AND state='done';\"",
    timeout=60, name='sql-cnt')
print(out)
