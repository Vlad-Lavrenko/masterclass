from odoo import api, models


class PricelistItem(models.Model):
    _inherit = "product.pricelist.item"

    @api.model_create_multi
    def create(self, vals_list):
        res = super().create(vals_list) 
        if not self.env.context.get('no_update_offer_state'):
            if res.product_id:
                product_ids = res.product_id.mapped('id')
            else:
                product_ids = res.product_tmpl_id.product_variant_ids.mapped('id')    

            pricelist_ids = res.pricelist_id.mapped('id')
            marketplace_ids = self.env['td.marketplace.pricelist'].search(domain = [('pricelist_id','in', pricelist_ids)]).mapped('marketplace_id.id')
            offer_ids = self.env['td.offer'].search(domain=[('marketplace_id','in',marketplace_ids), ('product_id','in',product_ids)])
            # offer_ids.state = 'to_process'
            for offer in offer_ids:
                if offer.state != 'to_process':
                    offer.state = 'to_process_stock'
        return res

    def write(self, values):
        res = super().write(values)

        if not self.env.context.get('no_update_offer_state'):
            if self.product_id:
                product_ids = self.product_id.mapped('id')
            else:
                product_ids = self.product_tmpl_id.product_variant_ids.mapped('id')    
            
            pricelist_ids = self.pricelist_id.mapped('id')
            marketplace_ids = self.env['td.marketplace.pricelist'].search(domain = [('pricelist_id','in', pricelist_ids)]).mapped('marketplace_id.id')
            offer_ids = self.env['td.offer'].search(domain=[('marketplace_id','in',marketplace_ids), ('product_id','in',product_ids)])
            # offer_ids.state = 'to_process'
            for offer in offer_ids:
                if offer.state != 'to_process':
                    offer.state = 'to_process_stock'
        return res
