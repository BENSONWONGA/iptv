# -*- coding: utf-8 -*-
{
    "name": "奥登科·现场派工",
    "version": "20.0.2.0.1",
    "category": "Manufacturing/Inventory",
    "summary": "现场管理应用：冲裁/手工/工艺派工单 + 派工领料 + 指令部件出入库 + 派工日报/件资产量 + 指令部件条码(H25/H27)扫码作业",
    "description": """对齐旧系统「现场管理」导航体系（H01-H43）：
1. 派工单三类：冲裁派工单、手工派工单、工艺派工单（H01-H04），
   状态流转：草稿 → 已派工 → 生产中 → 已完成；
2. 派工领料（H11-H15）：派工领料单/补料单/退料单/用量追加单
   复用仓库管理单据引擎，挂派工单自动过账库存；
3. 指令部件出入库（H41-H43）：指令部件入库单/出库单/库存表；
4. 日报及报表（H21-H26）：派工日报表（合格/不合格/工时/件资单价），
   日报确认自动累加完工数量，报满自动完工；件资产量汇总按操作员统计计件金额；
5. 指令部件条码（H25/H27）：派工单向导批量生成部件条码并打印标签（Code128）、
   多条码合并套码、PDA 扫码作业页 /odk/dispatch/scan
   （识别派工单/部件 → 部件出入库登记自动过账 → 扫码记录留痕）。""",
    "author": "奥登科",
    "license": "LGPL-3",
    "depends": ["odk_wms", "mrp", "web"],
    "data": [
        "security/ir.access.csv",
        "data/sequence.xml",
        "views/dispatch_views.xml",
        "views/barcode_views.xml",
        "views/scan_parts_page.xml",
        "report/barcode_report.xml",
    ],
    "installable": True,
    "application": True,
}
