import sys
sys.path.insert(0, '/workspace')
from deploy_rpc import OdooRPC

rpc = OdooRPC('http://127.0.0.1:8095', 'shoe_test', 'admin', 'admin')
rpc.authenticate()

tests = [
    ('t1', '<search><field name="x_name"/></search>'),
    ('t2', """<search><filter name="iqc" string="来料" domain="[('x_inspection_type','=','iqc')]"/></search>"""),
    ('t3', """<search><group expand="0" string="分组"><field name="x_inspection_type"/></group></search>"""),
    ('t4', '<search><field name="x_name" string="单号"/><field name="x_product_id"/></search>'),
    ('t5', """<search><separator/><filter name="fail" string="不合格" domain="[('x_result','=','fail')]"/></search>"""),
    ('t6', """<search><group expand="0" string="分组"><filter name="g1" string="按类型" groupby="x_inspection_type"/></group></search>"""),
]
for name, arch in tests:
    try:
        vid = rpc.create('ir.ui.view', {'name': 'x_test_%s' % name, 'model': 'x_qc_inspection',
                                        'type': 'search', 'arch_db': arch})
        print(name, 'OK')
        rpc.call('ir.ui.view', 'unlink', [[vid]])
    except Exception as e:
        print(name, 'FAIL:', str(e)[:200])
