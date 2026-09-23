from odoo import models, fields
import logging

_logger = logging.getLogger('-= Marketplace Import Wizard')


class MarketplaceImportWizard(models.TransientModel):
    _name = 'td.marketplace.import.wizard'
    _description = "Marketplace's Data Import Wizard"

    marketplace_id = fields.Many2one(
            comodel_name='td.marketplace', 
            string = 'Marketplace', 
            readonly = True,
        )

    page = fields.Integer(
            string = 'Page',
            default = 1
        )

    per_page = fields.Integer(
            string = 'Records per Page',
            default = 50
        )

    do_update = fields.Boolean(
            string = 'Update existing records',
            default = False
        )    

    procedure = fields.Char(
            string = 'Procedure name',
            readonly = True,
        )    

    procedure_description = fields.Char(
            string = 'Data description',
            readonly = True,
        )    

    site_id = fields.Char(
            string='Site ID',
        )    

    def action_import_page(self):
        if not hasattr(self.marketplace_id, f'{self.procedure}'):
            return False

        if self.site_id:
            site_ids = self.site_id.split(',')
            for site_id in site_ids:
                getattr(self.marketplace_id, f'{self.procedure}')(self.page, self.per_page, self.do_update, site_id,) 

            return {
                'type': 'ir.actions.act_window',
                'res_model': 'td.marketplace.import.wizard',
                'view_mode': 'form',
                'target': 'new',
                'res_id': self.id,
                'context': self.env.context,
            }    

        else:
            if getattr(self.marketplace_id, f'{self.procedure}')(self.page, self.per_page, self.do_update, self.site_id,):
                self.page += 1
                return {
                    'type': 'ir.actions.act_window',
                    'res_model': 'td.marketplace.import.wizard',
                    'view_mode': 'form',
                    'target': 'new',
                    'res_id': self.id,
                    'context': self.env.context,
                }    

    def action_import_all(self, page=1, per_page=50, do_update=False):

        _use_logging = (self.env['ir.config_parameter'].sudo().get_param('td_marketplace.mc_use_logging') == 'True')
        self.marketplace_id._add_log(_use_logging, _logger, 'Start import: page ' + f'{page}' + ', per page ' + f'{per_page}')

        if not hasattr(self.marketplace_id, f'{self.procedure}'):
            return False

        return getattr(self.marketplace_id, f'{self.procedure}')(page, per_page, do_update)            
