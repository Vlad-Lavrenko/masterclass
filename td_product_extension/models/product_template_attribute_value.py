from odoo import models


class ProductTemplateAttributeValue(models.Model):
    _inherit = 'product.template.attribute.value'

    def _without_no_variant_attributes(self):
        return self.filtered(lambda ptav: ptav.attribute_line_id.td_make_variant == True)


