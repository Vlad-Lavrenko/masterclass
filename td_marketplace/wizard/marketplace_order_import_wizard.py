from odoo import api, models, fields, _
import logging


class MarketplaceOrderImportWizard(models.TransientModel):
    _name = 'td.marketplace.order.import.wizard'
    _description = "Marketplace's Order Import Wizard"

    marketplace_id = fields.Many2one(
            comodel_name='td.marketplace', 
            string = 'Marketplace', 
            readonly = True,
        )

    marketpalce_order_sync = fields.Selection(
            string = 'Marketplace order sync',
            related = 'marketplace_id.order_sync',
        )

    last_sync_date = fields.Datetime(
            string = 'Last sync date',
        )    

    last_sync_id = fields.Integer(
            string = 'Last sync id',
        )    

    def action_import_order(self):
        if not hasattr(self.marketplace_id, f'{self.marketplace_id.code}_actualize_orders'):
            return

        if self.marketpalce_order_sync == 'date':
            sync_data = {
                'sync_by': 'date',
                'sync': self.last_sync_date,
            }
        elif self.marketpalce_order_sync == 'id':   
            sync_data = {
                'sync_by': 'id',
                'sync': self.last_sync_id,
            }
        else:
            return

        getattr(self.marketplace_id, f'{self.marketplace_id.code}_actualize_orders')(sync_data)    
        self._compute_last_sync()

        return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _("Order import"),
                    'type': 'success',
                    'message': _("Imported"),
                    'sticky': False,
                },
            }

    @api.model
    def default_get(self, fields_list):
        res = super(MarketplaceOrderImportWizard, self).default_get(fields_list)

        return res

    @api.depends('marketplace_id')
    @api.onchange('marketplace_id')
    def _compute_last_sync(self):
        last_sync_data = self.marketplace_id._get_last_sync_data()
        if self.marketpalce_order_sync == 'date':
            self.last_sync_date = last_sync_data['sync']
        elif self.marketpalce_order_sync == 'id':   
            self.last_sync_id = last_sync_data['sync']    
            

