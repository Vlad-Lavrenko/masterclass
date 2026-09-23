from odoo import fields, models, api

class MarketplaceCategory(models.Model):
    _name = 'td.marketplace.category'
    _description = 'Marketplace category'
    _rec_name = 'full_name'

    name = fields.Char()
    code = fields.Integer()
    ref = fields.Char()
    full_name = fields.Char()

    marketplace_id = fields.Many2one(
            comodel_name='td.marketplace', 
            ondelete='cascade',
        )
    parent_id = fields.Many2one(
            comodel_name='td.marketplace.category', 
        )

    def compute_full_name(self):
        for obj in self:
            if obj.parent_id:
                obj.full_name = obj.parent_id.full_name + ' / ' + obj.name
            else:    
                obj.full_name = obj.name

class MarketplaceCategoryProduct(models.Model):

    _name = 'td.marketplace.category.product'
    _description = 'Marketplace`s Category`s Products'

    marketplace_id = fields.Many2one(
            comodel_name='td.marketplace', 
            required=True, 
            ondelete='cascade',
        )

    category_id = fields.Many2one(
            comodel_name='td.marketplace.category', 
            required=True, 
            ondelete='cascade',
        )

    product_tmpl_id = fields.Many2one(
            comodel_name='product.template', 
            required=True, 
            ondelete='cascade',
        )    

    def write(self, vals):
        res = super().write(vals)

        if not self.env.context.get('no_update_offer_state'):
            if self.product_tmpl_id.product_variant_count == 1:
                offer_ids = self.env['td.offer'].search(domain=[('product_id','=',self.product_tmpl_id.product_variant_id.id), ('marketplace_id','=',self.marketplace_id.id)])
            else:
                product_ids = self.product_tmpl_id.product_variant_ids.mapped('id')
                offer_ids = self.env['td.offer'].search(domain=[('product_id','in',product_ids), ('marketplace_id','=',self.marketplace_id.id)])
            offer_ids.state = 'to_process'

        return res

    @api.model_create_multi
    def create(self, vals_list):
        res = super().create(vals_list)  
        
        if not self.env.context.get('no_update_offer_state'):
            for vals in vals_list:
                product_tmpl_id = self.env['product.template'].browse(vals['product_tmpl_id'])
                if product_tmpl_id.product_variant_count == 1:
                    offer_ids = self.env['td.offer'].search(domain=[('product_id','=',product_tmpl_id.product_variant_id.id), ('marketplace_id','=',vals['marketplace_id'])])

                else:
                    product_ids = product_tmpl_id.product_variant_ids.mapped('id')
                    offer_ids = self.env['td.offer'].search(domain=[('product_id','in',product_ids), ('marketplace_id','=',vals['marketplace_id'])])
                offer_ids.state = 'to_process'

        return res
