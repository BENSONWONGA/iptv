# -*- coding: utf-8 -*-
"""修正币种：科目表 ALL -> CNY，然后公司币种 -> CNY"""
from api import get_list, set_doc, get_doc, new_doc

COMPANY = "奥登科鞋业有限公司"

# 1. 批量修改公司科目币种
accounts = get_list("Account", fields=["name", "account_currency", "is_group"],
                    filters=[["account_currency", "=", "ALL"], ["company", "=", COMPANY]], limit=500)
print(f"ALL 币种科目数: {len(accounts)}")
ok, fail = 0, 0
for a in accounts:
    if a["is_group"]:
        continue
    try:
        set_doc("Account", a["name"], {"account_currency": "CNY"})
        ok += 1
    except Exception as e:
        fail += 1
        print("  FAIL:", a["name"], str(e)[:120])
print(f"科目币种改 CNY: 成功 {ok}, 失败 {fail}")

# 2. 修改公司币种
try:
    set_doc("Company", COMPANY, {"default_currency": "CNY"})
    print("公司币种 -> CNY 成功")
except Exception as e:
    print("公司币种修改失败:", str(e)[:300])

# 3. 验证
c = get_doc("Company", COMPANY)
print("验证公司币种:", c.get("default_currency"))

# 4. 创建客户分组和客户（修正父分组名）
try:
    get_doc("Customer Group", "外贸客户")
    print("客户分组已存在")
except Exception:
    new_doc("Customer Group", {"customer_group_name": "外贸客户",
                               "parent_customer_group": "所有客户群组", "is_group": 0})
    print("创建客户分组: 外贸客户")

try:
    get_doc("Customer", "美星国际贸易有限公司")
    print("客户已存在")
except Exception:
    new_doc("Customer", {
        "customer_name": "美星国际贸易有限公司",
        "customer_type": "Company",
        "customer_group": "外贸客户",
        "territory": "世界其他地区",
    })
    print("创建客户: 美星国际贸易有限公司")
