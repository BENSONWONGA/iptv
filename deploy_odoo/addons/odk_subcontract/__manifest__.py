# 奥登科·委外加工 —— Odoo 20 社区版委外补齐模块
# 功能：选委外供应商 + 成品 + BOM 自动带出组件 → 确认即发料出库 → 收货即成品入库
{
    "name": "奥登科·委外加工",
    "version": "20.0.1.0.0",
    "category": "Manufacturing/Manufacturing",
    "summary": "委外加工单：BOM 自动发料给委外供应商，成品收货自动入库（社区版 mrp_subcontracting 替代件）",
    "description": """为社区版补齐企业版 mrp_subcontracting 的核心场景（鞋业裁断/针车/成型外发）：
1. 选择委外供应商、成品、数量，按 BOM 自动带出组件物料明细（可改）；
2. 点击“确认发料”生成并过账发料调拨单：材料仓 → 委外供应商；
3. 点击“成品收货”生成并过账收货单：委外供应商 → 成品仓；
4. 加工单价与金额自动汇总，库存账实联动，全程可追溯。""",
    "author": "奥登科",
    "license": "LGPL-3",
    "depends": ["stock", "mrp"],
    "data": [
        "security/ir.access.csv",
        "data/sequence.xml",
        "views/subcontract_views.xml",
    ],
    "installable": True,
    "application": True,
}
