from odoo import fields, models

class MarketplaceProdcutField(models.Model):
    _inherit = 'td.marketplace.product.field'

    oc_seo_url = fields.Char(
            string='SEO URL', 
            translate=True,
        )

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

    oc_tag = fields.Char(
            string='Tags', 
            translate=True,
        )            

    oc_date_available = fields.Datetime(
            string='Date available', 
        )    
