from odoo import models

class StockQuant(models.Model):
    _inherit = 'stock.quant'

    def write(self, vals):

        res = super().write(vals)

        if not self.env.context.get('no_update_offer_state'):
            self.env['td.offer'].search(
                domain=[('product_id', 'in', self.product_id.ids)]
            )._queue_stock_update()
        return res
