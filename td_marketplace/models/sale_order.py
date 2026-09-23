from odoo import fields, models


class SaleOrder(models.Model):
    _inherit = "sale.order"

    td_marketplace_id = fields.Many2one(
            comodel_name='td.marketplace', 
            string='Marketplace',
            ondelete='cascade',
            readonly=True,
        )

    td_marketplace_number = fields.Char(
            string = 'Marketplace #',
            readonly=True,
        )    

    td_marketplace_code = fields.Integer(
            string='Marketplace id',
            readonly=True,
        )      
        
    td_marketplace_warning = fields.Boolean(
            string='Warning',
        )          

    def _action_cancel(self):
        res = super()._action_cancel()
        self._td_queue_offers_stock_update()
        return res

    def _td_queue_offers_stock_update(self):
        """Put every offer of the ordered products in the stock-update queue.

        Cancelling an order releases the goods, but on the marketplace side the
        quantity was already reduced when the order was placed. Nothing in
        `stock.quant` changes for an order cancelled before delivery, so the
        queue is filled here instead.
        """
        if self.env.context.get('no_update_offer_state'):
            return

        product_ids = self.order_line.product_id
        if not product_ids:
            return

        self.env['td.offer'].search(
            domain=[('product_id', 'in', product_ids.ids)]
        )._queue_stock_update()
