{
    "name": "奥登科·技转管理",
    "version": "20.0.1.0.0",
    "category": "Manufacturing/Inventory",
    "summary": "鞋业技转架构：量产确认单 / 确认变更单 / 材料替换 / 部件工艺流程单 / 鞋款SOP / 楦模档案 / 量产试做单 / 试做进度",
    "description": """把传统鞋厂技转部业务搬到 Odoo 20：
D01 量产确认单、D02 确认变更单(ECN)、D06 确认单工序设置、
D07 确认单材料替换、D04 鞋款SOP管理、D09 部件工艺流程单、
试做与进度（量产试做单 / 新款产前试做进度 / AOK进度）、楦模档案。""",
    "author": "奥登科",
    "license": "LGPL-3",
    "depends": ["mrp"],
    "data": [
        "security/ir.access.csv",
        "data/sequence.xml",
        "views/tech_views.xml",
    ],
    "installable": True,
    "application": True,
}
