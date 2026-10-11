{
    'name': '鞋厂研发管理 PLM',
    'version': '20.0.1.0.0',
    'category': 'Manufacturing/PLM',
    'summary': '工程变更单(ECO)管理：设计/工艺/材料变更审批与执行',
    'description': """鞋业研发管理（轻量 PLM）：
- 工程变更单 ECO：设计变更/工艺变更/材料替代/图纸纠错
- 完整审批流：草稿 → 评审 → 批准 → 执行
- 执行时自动克隆新版本 BOM 并归档旧版本
- 技术图纸/资料附件管理
- BOM 表单上显示关联的变更历史""",
    'author': 'Benson Shoe Factory',
    'depends': ['mrp', 'mail'],
    'data': [
        'security/shoe_plm_security.xml',
        'security/ir.access.csv',
        'data/sequence_data.xml',
        'views/plm_views.xml',
        'views/mrp_bom_views.xml',
    ],
    'application': True,
    'license': 'LGPL-3',
}
