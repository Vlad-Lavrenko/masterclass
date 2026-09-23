# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, _


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    td_marketplace_warning = fields.Boolean(
            string='Warning',
        )