# 奥登科·扫码出入库 —— Odoo 20 社区版条码/PDA 替代件
# 功能：扫条码 → 识别物料 → 选源仓/目标仓 → 提交生成并过账库存调拨单
{
    "name": "奥登科·扫码出入库",
    "version": "20.0.1.0.0",
    "category": "Inventory/Inventory",
    "summary": "扫条码识别物料，选源仓→目标仓提交，自动生成并过账库存调拨单（社区版条码替代件）",
    "description": "为社区版补齐企业版条码 App 的核心场景：仓库用扫码枪/PDA 扫物料条码，选择从哪个仓到哪个仓，一键生成已过账的库存调拨。支持工厂指令单号关联便于追溯。",
    "author": "奥登科",
    "license": "LGPL-3",
    "depends": ["stock"],
    "data": [
        "security/ir.access.csv",
        "views/scan_page.xml",
    ],
    "installable": True,
    "application": True,
}
