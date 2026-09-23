from odoo import models, fields


class MarketplaceExportWizard(models.TransientModel):
    _name = 'td.marketplace.export.wizard'
    _description = "Marketplace's Data Export Wizard"

    marketplace_id = fields.Many2one(
            comodel_name='td.marketplace', 
            string = 'Marketplace', 
            readonly = True,
        )

    export_type = fields.Selection(
            selection=[('update', 'Update'), ('update_stock', 'Update stock')],
            string='Export type',
            readonly = True,
        )    

    comment = fields.Char(
            string='Comment',
            # readonly = True,
        )    

    def action_do_update(self):
        return self.marketplace_id._action_do_update()

    def action_do_update_stock(self):
        return self.marketplace_id._action_do_update_stock()
