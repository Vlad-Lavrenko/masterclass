from odoo import fields, models


class ProductTemplateAttributeLine(models.Model):
    _inherit = 'product.template.attribute.line'

    td_make_variant = fields.Boolean(
            string="Variant", 
            default=False,
        )

    def _without_no_variant_attributes(self):
        # return self.filtered(lambda ptal: ptal.attribute_id.create_variant != 'no_variant' or (ptal.attribute_id.create_variant == 'no_variant' and ptal.td_make_variant))
        return self.filtered(lambda ptal: ptal.td_make_variant)


