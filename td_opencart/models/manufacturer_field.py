from odoo import api, fields, models

class MarketplaceManufacturerField(models.Model):
    _inherit = 'td.marketplace.manufacturer.field'

    oc_meta_description = fields.Char(
            string='META Description', 
            translate=True,
        )

    oc_meta_keywords = fields.Char(
            string='META Keywords', 
            translate=True,
        )

    oc_meta_title = fields.Char(
            string='META Title', 
            translate=True,
        )
