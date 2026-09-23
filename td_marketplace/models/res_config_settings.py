from odoo import api, fields, models

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    td_mc_use_logging = fields.Boolean(
        string='Use logging',
        config_parameter='td_marketplace.mc_use_logging',        
    )    