{
    'name': '鞋厂质量管理 QMS',
    'version': '20.0.1.0.0',
    'category': 'Manufacturing/Quality',
    'summary': '来料/制程/成品/出货检验与不合格品处置',
    'description': """鞋业加工厂质量管理系统：
- 来料检验(IQC) / 制程检验(IPQC) / 成品检验(FQC) / 出货检验(OQC)
- 内置鞋业标准检验项目模板，自动生成检验项
- 不合格品处置单(NCR)：返工/让步接收/报废/退货/挑选
- 与库存调拨、生产工单、批次关联""",
    'author': 'Benson Shoe Factory',
    'depends': ['mrp', 'mail'],
    'data': [
        'security/shoe_qms_security.xml',
        'security/ir.access.csv',
        'data/sequence_data.xml',
        'views/qc_views.xml',
    ],
    'application': True,
    'license': 'LGPL-3',
}
