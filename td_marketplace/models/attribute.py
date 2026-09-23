from odoo import fields, models

class MarketplaceAttribute(models.Model):
    _name = 'td.marketplace.attribute'
    _description = "Marketplace attribute"

    marketplace_id = fields.Many2one(
            comodel_name='td.marketplace', 
            ondelete='cascade',
        )
    attribute_id = fields.Many2one(
            comodel_name='product.attribute',
            string = 'Attribute',
            ondelete='cascade',
        )   

    marketplace_code = fields.Char(
            string='Marketplace id'
        )    

    prefix = fields.Char(
            string='Prefix',
        )

    def action_upload_attribute(self):
        self.marketplace_id.upload_attribute(self)
