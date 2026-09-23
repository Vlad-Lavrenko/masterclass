from odoo import fields, models

class MarketplacePartner(models.Model):
    _name = 'td.marketplace.partner'
    _description = "Marketplace partner"

    marketplace_id = fields.Many2one(
            comodel_name='td.marketplace', 
            ondelete='cascade',
        )
    partner_id = fields.Many2one(
            comodel_name='res.partner',
            string = 'Partner',
            ondelete='cascade',
        )   

    marketplace_code = fields.Char(
            string='Marketplace id'
        )    
