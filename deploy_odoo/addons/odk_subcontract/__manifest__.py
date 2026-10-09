# 奥登科·委外加工 —— Odoo 20 社区版委外补齐模块
# v2：对齐旧系统委外管理架构——五类单据 + 制程工艺报价 + 补耗关联 + 追踪报表 + 独立应用
{
    "name": "奥登科·委外管理",
    "version": "20.0.2.0.0",
    "category": "Manufacturing/Manufacturing",
    "summary": "独立委外管理应用：材料合成/部件/制程/补耗/外采五类单据、制程工艺报价、外发追踪、执行状况报表、部件配套欠数查询",
    "description": """对齐旧系统委外管理架构（社区版 mrp_subcontracting 替代件）：
1. 五类单据：材料合成加工单 / 部件外发加工 / 制程外发加工 / 制程补耗加工 / 外采订单
   ——统一流程：BOM 自动带组件 → 确认发料（材料出库）→ 成品收货（成品入库）；
2. 外采指令单 = 外采草稿单；确认发料 = 外采领料单；收货 = 外采收货单；
3. 制程补耗加工：关联补耗来源单，复制组件与供应商，加工费清零，独立核算损耗；
4. 制程工艺报价：委外工序单价档案，下单一键带出供应商/成品/单价，支持有效期内查询；
5. 报表：外发加工追踪表（超期预警）、委外执行状况表（透视）、部件配套欠数查询（联动 MRP 运算）；
6. 独立「委外管理」应用，菜单结构对齐旧系统。""",
    "author": "奥登科",
    "license": "LGPL-3",
    "depends": ["stock", "mrp", "odk_mrp_calc"],
    "data": [
        "security/ir.access.csv",
        "data/sequence.xml",
        "views/quote_views.xml",
        "views/subcontract_views.xml",
    ],
    "installable": True,
    "application": True,
}
