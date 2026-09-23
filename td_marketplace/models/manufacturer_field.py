from odoo import api, fields, models

class MarketplaceManufacturerField(models.Model):
    _name = 'td.marketplace.manufacturer.field'
    _description = "Marketplace Manufacturer Fields"

    marketplace_id = fields.Many2one(
            comodel_name='td.marketplace', 
            required=True, 
            ondelete='cascade',
        )

    manufacturer_id = fields.Many2one(
            comodel_name='td.manufacturer', 
            required=True, 
            ondelete='cascade',
        )    

    _sql_constraints = [
        ('unique_marketplace_manufacturer', 'UNIQUE (marketplace_id, manufacturer_id)', 'Additional fields contain repeating lines for the marketplace.')
    ]

    @api.model_create_multi
    def create(self, vals_list):
        res = super().create(vals_list) 
        if not self.env.context.get('no_update_offer_state'):
            for obj in res:
                manufacturer_id = obj.manufacturer_id.id
                marketplace_id = obj.marketplace_id.id  
                mp_manufacturer_ids = self.env['td.marketplace.manufacturer'].search(domain=[('marketplace_id','=',marketplace_id), ('manufacturer_id','=',manufacturer_id)])
                mp_manufacturer_ids.state = 'to_process'
        return res

    def write(self, vals):
        res = super().write(vals)
        if not self.env.context.get('no_update_offer_state') and res:
            manufacturer_id = self.manufacturer_id.id
            marketplace_id = self.marketplace_id.id  
            mp_manufacturer_ids = self.env['td.marketplace.manufacturer'].search(domain=[('marketplace_id','=',marketplace_id), ('manufacturer_id','=',manufacturer_id)])
            mp_manufacturer_ids.state = 'to_process'
        return res
