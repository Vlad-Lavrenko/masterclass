from odoo import models, fields, api

class MarketplaceCategoryProductWizard(models.TransientModel):
    _name = 'td.marketplace.category.product.wizard'
    _description = "Marketplace's Category's Product Wizard"

    marketplace_id = fields.Many2one(
            comodel_name='td.marketplace', 
            string = 'Marketplace', 
            domain="[('id', 'in', available_marketplace_ids)]"            
        )

    category_id = fields.Many2one(
            comodel_name='td.marketplace.category', 
            string = 'Category', 
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
                marketplace_ids= self.env['td.offer'].search(domain=[('product_id','=',self.product_id.product_variant_id.id)]).mapped('marketplace_id')
            else:
                product_ids = self.product_id.product_variant_ids.mapped('id')
                marketplace_ids = self.env['td.offer'].search(domain=[('product_id','in',product_ids)]).mapped('marketplace_id')
            # marketplace_ids = self.env['td.offer'].search(domain=[('product_id','=',self.product_id.id)]).mapped('marketplace_id')
            self.available_marketplace_ids = marketplace_ids     

    @api.depends('marketplace_id')
    @api.onchange('marketplace_id')
    def _compute_default_category(self):
        if self.marketplace_id:
            category_ids = self.env['td.marketplace.category.product'].search(domain=[('product_tmpl_id','=',self.product_id.id), ('marketplace_id','=',self.marketplace_id.id)]).mapped('category_id')
            if category_ids:
                self.category_id = category_ids[0]

    def action_apply(self):    
        ref_id = self.env['td.marketplace.category.product'].search(domain=[('product_tmpl_id','=',self.product_id.id), ('marketplace_id','=',self.marketplace_id.id)]).mapped('id') 
        if ref_id:
            obj = self.env['td.marketplace.category.product'].browse(ref_id)
            obj.write({'category_id': self.category_id.id})
        else:
            self.env['td.marketplace.category.product'].create({
                    'marketplace_id': self.marketplace_id.id,
                    'product_tmpl_id': self.product_id.id,
                    'category_id': self.category_id.id,
                })    
