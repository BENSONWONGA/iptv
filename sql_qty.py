#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""SQL 查猎鹰TX 真实库存分布"""
from bt_exec import BTExec

ex = BTExec()
out = ex.run(
    "sudo -u postgres psql benson -c \""
    "SELECT pp.id, pp.id AS variant_id, COALESCE(SUM(sq.quantity),0) AS qty "
    "FROM product_product pp "
    "LEFT JOIN stock_quant sq ON sq.product_id = pp.id AND sq.location_id IN "
    "(SELECT id FROM stock_location WHERE usage='internal') "
    "WHERE pp.product_tmpl_id = (SELECT id FROM product_template WHERE default_code='ADK-T001') "
    "GROUP BY pp.id ORDER BY pp.id;\" 2>&1; "
    "sudo -u postgres psql benson -c \""
    "SELECT sq.product_id, sl.complete_name, sq.quantity FROM stock_quant sq "
    "JOIN stock_location sl ON sl.id=sq.location_id "
    "WHERE sq.product_id IN (SELECT id FROM product_product WHERE product_tmpl_id="
    "(SELECT id FROM product_template WHERE default_code='ADK-T001')) AND sq.quantity != 0;\" 2>&1",
    timeout=60, name='sql-qty')
print(out)
