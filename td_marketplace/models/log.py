from odoo import fields, models


class MarketplaceLog(models.Model):
    _name = 'td.marketplace.log'
    _description = 'Marketplace log'
    _order = 'create_date DESC'

    marketplace_id = fields.Many2one(
            comodel_name='td.marketplace', 
            string='Marketplace',
            ondelete='cascade',   
        )
    name = fields.Char(string='URL', )
    json = fields.Text()
    params = fields.Text()
    headers = fields.Text()
    error = fields.Text()
    response = fields.Text()
    response_headers = fields.Text()
    method = fields.Char()
    called_method = fields.Char()
    code = fields.Char()
