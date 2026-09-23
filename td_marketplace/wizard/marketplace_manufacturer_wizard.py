from odoo import models, fields, api

class MarketplaceManufacturerWizard(models.TransientModel):
    _name = 'td.marketplace.manufacturer.wizard'
    _description = "Marketplace's Manufacturer Wizard"

    marketplace_id = fields.Many2one(
            comodel_name='td.marketplace', 
            string = 'Marketplace', 
            domain="[('id', 'in', available_marketplace_ids)]"            
        )

    manufacturer_id = fields.Many2one(
            comodel_name='td.manufacturer', 
            string = 'Manufacturer', 
            default = lambda self: self.env.context.get('default_manufacturer_id')
        )   

    available_marketplace_ids = fields.Many2many(
            comodel_name='td.marketplace', 
            compute='_compute_available_marketplace_ids'
        )                 

    @api.depends('manufacturer_id')
    def _compute_available_marketplace_ids(self):  
        if self.manufacturer_id:
            marketplace_manufacturer_ids= self.env['td.marketplace.manufacturer'].search(domain=[('manufacturer_id','=',self.manufacturer_id.id)]).mapped('marketplace_id')
            marketplace_ids = self.env['td.marketplace'].search(domain=[])
            self.available_marketplace_ids = marketplace_ids - marketplace_manufacturer_ids

    def action_apply(self):    
        if self.manufacturer_id and self.marketplace_id:
            self.env['td.marketplace.manufacturer'].create({
                                            'marketplace_id': self.marketplace_id.id,
                                            'manufacturer_id': self.manufacturer_id.id,
                                            'state': 'to_process',
                                        })