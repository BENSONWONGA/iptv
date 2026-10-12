# -*- coding: utf-8 -*-
{
    'name': '鞋厂主题与驾驶舱 (Shoe Factory Theme & Dashboard)',
    'version': '20.0.1.0.0',
    'category': 'Theme',
    'summary': '深紫渐变玻璃拟态主题 + 鞋厂 KPI 驾驶舱仪表盘',
    'description': """
玻璃拟态深色主题：全局渐变背景、玻璃卡片、圆角视图
KPI 驾驶舱：本月销售/报价单/欠款/生产工单/检验单/活动/任务/联系人 + 快捷入口 + 月度销售图表 + 最新订单
    """,
    'author': 'Benson Shoe Factory',
    'depends': ['web', 'sale_management', 'purchase', 'mrp', 'account', 'project', 'hr'],
    'data': [
        'views/dashboard_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'shoe_theme/static/src/css/glass_theme.css',
            'shoe_theme/static/src/css/dashboard.css',
            'shoe_theme/static/src/xml/dashboard.xml',
            'shoe_theme/static/src/js/dashboard.js',
        ],
    },
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}
