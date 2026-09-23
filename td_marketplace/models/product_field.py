from odoo import api, fields, models

class MarketplaceProdcutField(models.Model):
    _name = 'td.marketplace.product.field'
    _description = "Marketplace Products Fields"

    marketplace_id = fields.Many2one(
            comodel_name='td.marketplace', 
            required=True, 
            ondelete='cascade',
        )

    product_tmpl_id = fields.Many2one(
            comodel_name='product.template', 
            required=True, 
            ondelete='cascade',
        )    

    _sql_constraints = [
        ('unique_marketplace_product', 'UNIQUE (marketplace_id, product_tmpl_id)', 'Additional fields contain repeating lines for the marketplace.')
    ]

    @api.model_create_multi
    def create(self, vals_list):
        res = super().create(vals_list) 
        if not self.env.context.get('no_update_offer_state'):
            for obj in res:
                product_tmpl_id = obj.product_tmpl_id.id
                marketplace_id = obj.marketplace_id.id  
                offer_ids = self.env['td.offer'].search(domain=[('marketplace_id','=',marketplace_id), ('product_tmpl_id','=',product_tmpl_id)])
                offer_ids.state = 'to_process'
        return res


    def write(self, values):
        res = super().write(values)
        if not self.env.context.get('no_update_offer_state') and res:
            product_tmpl_id = self.product_tmpl_id.id
            marketplace_id = self.marketplace_id.id  
            offer_ids = self.env['td.offer'].search(domain=[('marketplace_id','=',marketplace_id), ('product_tmpl_id','=',product_tmpl_id)])
            offer_ids.state = 'to_process'
        return res
