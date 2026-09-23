from odoo import models, fields, api

class OfferWizard(models.TransientModel):
    _name = 'td.offer.wizard'
    _description = "Offer Product Wizard"

    marketplace_id = fields.Many2one(
            comodel_name='td.marketplace', 
            string = 'Marketplace', 
        )

    product_line = fields.One2many(
            comodel_name='td.offer.product.line', 
            inverse_name='offer_wizard_id',
        )

    @api.onchange('marketplace_id')
    def _compute_product_line(self):
        if self.marketplace_id:
            product_ids = self.env['product.template'].search(domain=[('detailed_type','=','product')])
            offer_product_ids = self.env['td.offer'].search(domain=[('marketplace_id','=',self.marketplace_id.id)]).mapped('product_id')
            if offer_product_ids:
                products = product_ids - offer_product_ids
            else:
                products = product_ids

            self.product_line = [(5, 0, 0)]
            lines = []

            for product in products:
                lines.append((0,0, {
                                    'offer_wizard_id': self.id,
                                    'check': True,
                                    'product_id': product.id,                    
                            }))

            self.product_line = lines                               

    def action_apply(self):
        for line in self.product_line:
            if line.check:
                self.env['td.offer'].create({
                            'marketplace_id': self.marketplace_id.id,
                            'product_id': line.product_id.id,
                            'state': 'to_process'
                        })

class OfferProduct(models.TransientModel):
    _name = 'td.offer.product.line'
    _description = "Offer product line"

    offer_wizard_id = fields.Many2one(
        comodel_name='td.offer.wizard',
        string="Offer Wizard Reference",
        required=False, ondelete='cascade', index=True, copy=False)

    check = fields.Boolean(
            string="Check",
            default=True,
        )    

    product_id = fields.Many2one(
            comodel_name='product.template', 
            string = 'Product', 
        )   




