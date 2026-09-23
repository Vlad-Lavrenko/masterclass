from odoo import models, fields, _

class Offer(models.Model):
    _name = 'td.offer'
    _description = 'Offer'

    active = fields.Boolean(
            default=True, 
        )

    state = fields.Selection(
            default='to_process', 
            readonly=True,
            selection=[
                        ('to_process_stock', _('To process stock')), 
                        ('to_process', _('To process')), 
                        ('to_process_all', _('To process all')), 
                        ('processed', _('Processed'))
                    ], 
        )

    marketplace_id = fields.Many2one(
            comodel_name='td.marketplace', 
            ondelete='cascade',
        )

    product_id = fields.Many2one(
            comodel_name='product.product', 
            required=True, 
            ondelete='cascade',
        )

    product_tmpl_id = fields.Many2one(
            comodel_name='product.template', 
            store=False,
            related='product_id.product_tmpl_id',
        )

    product_variant_value_ids = fields.Many2many(
            comodel_name='product.template.attribute.value',
            compute='_get_product_variant_value_ids',
            store=False,
        )    

    marketplace_code = fields.Char(
            string='Marketplace id'
        )    
    marketplace_variant_code = fields.Char(
            string='Marketplace variant id'
        )   

    def _get_product_variant_value_ids(self):
        for obj in self:
            obj.product_variant_value_ids = obj.product_id.product_template_variant_value_ids

    def action_set_to_process(self):
        self.state = 'to_process'    

    def action_set_to_process_stock(self):
        self.state = 'to_process_stock'    

    def action_set_to_process_all(self):
        self.state = 'to_process_all'    

    def action_set_processed(self):
        self.state = 'processed'    

    def _queue_stock_update(self):
        """Put the offers in the queue for a stock-only export.

        Raises the state instead of assigning it, so an export of the whole
        offer that is already pending is not lost.
        """
        for offer in self:
            if offer.state == 'to_process':
                offer.state = 'to_process_all'
            elif offer.state == 'processed':
                offer.state = 'to_process_stock'

    def unlink(self):
        for offer in self:
            self.env['td.marketplace.category.product'].search([
                                                                ('marketplace_id', '=', offer.marketplace_id.id),
                                                                ('product_tmpl_id', '=', offer.product_id.product_tmpl_id.id)
                                                            ]).unlink()
        
        return super(Offer, self).unlink()        
