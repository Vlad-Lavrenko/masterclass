from odoo import api, models, fields

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    td_manufacturer_id = fields.Many2one(
            string='Manufacturer',
            comodel_name='td.manufacturer',
        )

    td_length = fields.Float(
            string='Length',
        )    
    td_width = fields.Float(
            string='Width',
        )    
    td_height = fields.Float(
            string='Height',
        )   

    td_weight = fields.Float(
            string='Weight',
        )                       

    td_volume = fields.Float(
            string='Volume',
        )         

    td_uom_weight = fields.Many2one(
            comodel_name='uom.uom',
            string='Wegith Unit of Measure'
        )
    td_uom_volume = fields.Many2one(
            comodel_name='uom.uom',
            string='Volume Unit of Measure'
        )        

    td_uom_dimension = fields.Many2one(
            comodel_name='uom.uom',
            string='Dimension Unit of Measure'
        )                

    @api.depends('td_weight', 'td_uom_weight')
    def _compute_weight_depends(self):    
        self._compute_weight()

    @api.onchange('td_weight')
    def _compute_weight(self):    
        weight_uom = self._get_weight_uom_id_from_ir_config_parameter()
        for obj in self:
            if weight_uom != obj.td_uom_weight:
                obj.weight = obj.td_uom_weight._compute_quantity(obj.td_weight, weight_uom)
            else:    
                obj.weight = obj.td_weight
