from odoo import models, fields

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    td_marketplace_ids = fields.One2many(
            comodel_name='td.marketplace',
            compute='_compute_marketplace_ids',
            store=False,
        )

    td_marketplace_category_ids = fields.One2many(
            comodel_name='td.marketplace.category.product', 
            inverse_name='product_tmpl_id', 
        )   

    td_marketplace_filed_ids = fields.One2many(
            comodel_name='td.marketplace.product.field',
            inverse_name='product_tmpl_id', 
        )    

    def _compute_marketplace_ids(self):
        for obj in self:
            if obj.product_variant_count == 1:
                obj.td_marketplace_ids = self.env['td.offer'].search(domain=[('product_id','=',obj.product_variant_id.id)]).mapped('marketplace_id')
            else:
                product_ids = obj.product_variant_ids.mapped('id')
                obj.td_marketplace_ids = self.env['td.offer'].search(domain=[('product_id','in',product_ids)]).mapped('marketplace_id')

    def write(self, vals):

        res = super().write(vals)
        if not self.env.context.get('no_update_offer_state'):
            if self.product_variant_count == 1:
                offer_ids = self.env['td.offer'].search(domain=[('product_id','=',self.product_variant_id.id)])
                offer_ids.state = 'to_process'
            else:
                product_tmpl_offers_ids = self.env['td.offer'].search(domain=[('product_tmpl_id','=',self.id)])
                if product_tmpl_offers_ids:
                    for marketplace_id in product_tmpl_offers_ids.mapped('marketplace_id'):
                        marketplace_codes = product_tmpl_offers_ids.filtered(lambda x: x.marketplace_id == marketplace_id).mapped('marketplace_code')
                        if marketplace_codes:
                            marketplace_code = marketplace_codes[0]
                        else:    
                            marketplace_code = ''

                        for product_variant_id in self.product_variant_ids:
                            offer_id = self.env['td.offer'].search(domain=[('product_id','=',product_variant_id.id), ('marketplace_id','=',marketplace_id.id)])
                            if offer_id:
                                offer_id.state = 'to_process'
                            else:
                                offer_id = self.env['td.offer'].create({
                                            'product_id': product_variant_id.id,
                                            'marketplace_id': marketplace_id.id,
                                            'marketplace_code': marketplace_code,
                                            'state': 'to_process',
                                        }) 
                    # for product_variant_id in self.product_variant_ids:
                    #     offer_id = self.env['td.offer'].search(domain=[('product_id','=',product_variant_id.id)])
                    #     if offer_id:
                    #         offer_id.state = 'to_process'
                    #     else:
                    #         for marketplace_id in self.td_marketplace_ids:
                    #             offer_id = self.env['td.offer'].create({
                    #                         'product_id': product_variant_id.id,
                    #                         'marketplace_id': marketplace_id.id,
                    #                         'state': 'to_process',
                    #                     }) 
        return res

class ProductProduct(models.Model):
    _inherit = 'product.product'

    def write(self, vals):
        res = super().write(vals)
        if not self.env.context.get('no_update_offer_state'):
            for product in self:
                offer_ids = self.env['td.offer'].search(domain=[('product_id','=',product.id)])
                offer_ids.state = 'to_process'
        return res

