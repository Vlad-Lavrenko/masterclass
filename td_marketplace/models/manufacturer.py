from odoo import fields, models, _

class Manufacturer(models.Model):
    _inherit = 'td.manufacturer'

    td_marketplace_ids = fields.One2many(
            comodel_name='td.marketplace',
            compute='_compute_marketplace_ids',
            store=False,
        )

    td_marketplace_filed_ids = fields.One2many(
            comodel_name='td.marketplace.manufacturer.field',
            inverse_name='manufacturer_id', 
        )    

    def _compute_marketplace_ids(self):
        for obj in self:
            obj.td_marketplace_ids = self.env['td.marketplace.manufacturer'].search(domain=[('manufacturer_id','=',obj.id)]).mapped('marketplace_id')

    def write(self, vals):
        res = super().write(vals)
        if not self.env.context.get('no_update_offer_state'):
            mp_manufacturer_ids = self.env['td.marketplace.manufacturer'].search(domain=[('manufacturer_id','=',self.id)])
            mp_manufacturer_ids.state = 'to_process'

        return res

class MarketplaceManufacturer(models.Model):
    _name = 'td.marketplace.manufacturer'
    _description = "Marketplace manufacturer"

    marketplace_id = fields.Many2one(
            comodel_name='td.marketplace', 
            ondelete='cascade',
        )
    manufacturer_id = fields.Many2one(
            comodel_name='td.manufacturer',
            string = 'Manufacturer',
            ondelete='cascade',
        )   

    marketplace_code = fields.Char(
            string='Marketplace id'
        )   

    state = fields.Selection(
            default='to_process', 
            readonly=True,
            selection=[
                        ('to_process', _('To process')), 
                        ('processed', _('Processed'))
                    ], 
        )

    def action_set_to_process(self):
        self.state = 'to_process'    

    def action_set_processed(self):
        self.state = 'processed'    
