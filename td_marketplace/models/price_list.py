from odoo import api, fields, models
from odoo.exceptions import ValidationError


class MarketplacePricelist(models.Model):
    _name = 'td.marketplace.pricelist'
    _description = "Marketplace pricelist"

    marketplace_id = fields.Many2one(
            comodel_name='td.marketplace', 
            ondelete='cascade',
        )

    pricelist_id = fields.Many2one(
            comodel_name='product.pricelist', 
            ondelete='cascade',
        )

    marketplace_code = fields.Char(
            string='Marketplace id'
        )    

    pricelist_type = fields.Selection(
            selection=[('regular', 'regular'), ('sale', 'sale'), ('promotion','promotion')],
            required=True,
            default='sale',
        )

    @api.model
    def create(self, vals):
        if vals.get('pricelist_type') == 'regular':
            existing_pricelists = self.search([
                ('marketplace_id', '=', vals.get('marketplace_id')),
                ('pricelist_type', '=', 'regular')
            ])
            
            if existing_pricelists:
                raise ValidationError('There is already a price list with the type "regular" for this marketplace.')
        
        return super(MarketplacePricelist, self).create(vals)

    def write(self, vals):
        if vals.get('pricelist_type') == 'regular':
            for record in self:
                existing_pricelists = self.search([
                    ('marketplace_id', '=', record.marketplace_id.id),
                    ('pricelist_type', '=', 'regular'),
                    ('id', '!=', record.id)
                ])
                
                if existing_pricelists:
                    raise ValidationError('There is already a price list with the type "regular" for this marketplace.')

        return super(MarketplacePricelist, self).write(vals)      

    def action_upload_pricelist(self):
        self.marketplace_id.upload_pricelist(self)
