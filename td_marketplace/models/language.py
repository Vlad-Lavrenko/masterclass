from odoo import fields, models

class MarketplaceLanguage(models.Model):
    _name = 'td.marketplace.language'
    _description = "Marketplace language"

    marketplace_id = fields.Many2one(
            comodel_name='td.marketplace', 
            ondelete='cascade',
        )
    language_code = fields.Char(
            string = 'Language code'
        )   

    marketplace_code = fields.Char(
            string='Marketplace id'
        )    
    
