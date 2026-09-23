from odoo import models, fields, api

class MarketplaceOfferProductWizard(models.TransientModel):
    _name = 'td.marketplace.offer.product.wizard'
    _description = "Marketplace's Offer's Product Wizard"

    marketplace_id = fields.Many2one(
            comodel_name='td.marketplace', 
            string = 'Marketplace', 
            domain="[('id', 'in', available_marketplace_ids)]"            
        )

    product_id = fields.Many2one(
            comodel_name='product.template', 
            string = 'Product', 
            default = lambda self: self.env.context.get('default_product_id')
        )   

    available_marketplace_ids = fields.Many2many(
            comodel_name='td.marketplace', 
            compute='_compute_available_marketplace_ids'
        )                 

    @api.depends('product_id')
    def _compute_available_marketplace_ids(self):  
        if self.product_id:
            if self.product_id.product_variant_count == 1:
                marketplace_offer_ids= self.env['td.offer'].search(domain=[('product_id','=',self.product_id.product_variant_id.id)]).mapped('marketplace_id')
            else:
                product_ids = self.product_id.product_variant_ids.mapped('id')
                marketplace_offer_ids = self.env['td.offer'].search(domain=[('product_id','in',product_ids)]).mapped('marketplace_id')
            marketplace_ids = self.env['td.marketplace'].search(domain=[])
            self.available_marketplace_ids = marketplace_ids - marketplace_offer_ids    

    def action_apply(self):    
        if self.product_id and self.marketplace_id:
            product_ids = self.product_id.product_variant_ids
            for product in product_ids:
                self.env['td.offer'].create({
                                                'marketplace_id': self.marketplace_id.id,
                                                'product_id': product.id,
                                                'state': 'to_process',
                                            })
