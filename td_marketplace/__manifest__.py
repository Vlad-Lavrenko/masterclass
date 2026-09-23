{
    'name': 'Marketplace connector',
    'summary': 'Marketplace connector',
    'description': '',

    'author': 'ToDo',
    'website': 'todo.ltd',

    'category': 'Marketing',
    'license': 'OPL-1',
    'version': '17.0.1.0.35',

    'installable': True,
    'application': True,

    'assets':{
        'web.assets_backend': [
                'td_marketplace/static/src/import_button/*',
                'td_marketplace/static/src/export_button/*',
            ],
    },

    'images': [
        'static/description/banner.png',
    ],
    'depends': [
        'stock', 
        'sale',
        'sale_management',
        'product',
        'td_product_extension',
        'website_sale',
    ],
    'data': [
        "security/ir.model.access.csv",
        "views/category_views.xml",
        "views/marketplace_views.xml",
        "views/menu.xml",
        "views/offer_views.xml",
        "views/product_views.xml",
        "views/attribute_view.xml",
        "views/partner_views.xml",
        "wizard/marketplace_category_product_wizard.xml",
        "wizard/marketplace_offer_product_wizard.xml",
        "wizard/offer_wizard.xml",
        "wizard/marketplace_import_wizard.xml",
        "views/res_config_settings_views.xml",
        "views/sale_order_views.xml",
        "views/product_field_views.xml",
        "views/price_list_views.xml",
        "data/cron.xml",
        "views/log_views.xml",
        "wizard/marketplace_export_wizard.xml",
        "views/manufacturer_views.xml",
        "views/manufacturer_field_views.xml",
        "wizard/marketplace_manufacturer_wizard.xml",
        "wizard/marketplace_order_import_wizard.xml",
    ],
    'demo': [
    ],
}
