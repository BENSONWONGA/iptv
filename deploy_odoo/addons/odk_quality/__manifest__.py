# 奥登科·质量管理 —— Odoo 20 社区版质检补齐模块
# 功能：来料/制程/成品质检记录 + 不合格处置 + 质量异常单闭环
{
    "name": "奥登科·质量管理",
    "version": "20.0.1.0.0",
    "category": "Manufacturing/Manufacturing",
    "summary": "质检单（IQC/FQC）+ 质量异常单闭环（社区版 quality 替代件）",
    "description": """为社区版补齐企业版 Quality 的核心场景（鞋业来料检验、成品抽检）：
1. 质检单：关联库存单据/物料，记录抽检数、合格数、不合格数，自动判定结果；
2. 不合格可一键生成质量异常单，指明不良类型与责任供应商，闭环跟踪处理；
3. 列表直接汇总合格/不合格数量，抽检合格率一目了然。""",
    "author": "奥登科",
    "license": "LGPL-3",
    "depends": ["stock", "mrp"],
    "data": [
        "security/ir.access.csv",
        "data/sequence.xml",
        "views/quality_views.xml",
    ],
    "installable": True,
    "application": True,
}
