{
    'name': 'Test Module',
    'version': '17.0.0.1',
    'category': 'Uncategorized',
    'author': "Zesty Beanz Technology (P) Ltd.",
    'summary': 'Custom module for Savon',
    'description': "Custom module for Savon",
    "license": "LGPL-3",
    'depends': ['base','sale','stock'],
    'data': [
        'security/security.xml',
         'views/sale_order.xml',
         'views/res_config.xml'
,
    ],

    'installable': True,
    'auto_install': False,
}


