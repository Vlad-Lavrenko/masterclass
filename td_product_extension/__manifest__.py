{
    'name': 'Product Extension',
    'version': '17.0.1.0.7',
    'summary': 'Product extension',
    'description': '',
    'author': 'ToDo',
    'website': 'todo.ltd',
    'images': [
        'static/description/banner.png',
    ],
    'depends': [
        'product'
    ],
    'data': [
        "security/ir.model.access.csv",
        "views/menu.xml",
        "views/manufacturer_views.xml",
        "views/product_views.xml",
    ],
    'demo': [
    ],
    'installable': True,
    'application': True,
    'license': 'OPL-1',
}
