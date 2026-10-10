# -*- coding: utf-8 -*-
{
    "name": "奥登科·仓库管理",
    "version": "20.0.1.0.0",
    "category": "Manufacturing/Inventory",
    "summary": "独立仓库管理应用：采购入库/客供料/退料/领料/补料/试做/转卖/挪用/调拨/盘点等15类单据一键过账库存",
    "description": """对齐旧系统「材料库存管理」单据体系：
1. 入库类：采购入库单、客供料入库、综合入库单、生产退料入库、综合退料入库；
2. 出库类：加工领料单、补料领料单、试做领料单、综合领用单、指令领料单、
   采购退货单、客供料退货、材料转卖单、指令材料挪用单；
3. 调整类：物料转仓调拨单、盘点调整单（普通/指令）；
4. 查询：材料库存查询（在手/可用/在途）、待检记录报表（联动 IQC）、材料采购单（联动采购）；
5. 所有单据确认即自动生成并过账库存单据，库存账实联动。""",
    "author": "奥登科",
    "license": "LGPL-3",
    "depends": ["stock", "mrp", "purchase", "odk_quality"],
    "data": [
        "security/ir.access.csv",
        "data/sequence.xml",
        "views/wms_views.xml",
    ],
    "installable": True,
    "application": True,
}
