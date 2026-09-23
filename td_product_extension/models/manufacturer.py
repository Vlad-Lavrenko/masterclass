from odoo import fields, models

class Manufacturer(models.Model):
    _name = 'td.manufacturer'
    _description = "Manufacturer"

    name = fields.Char(
            string='Name',
            required = True,
        )
    description = fields.Html(
            string='Description', 
            translate=True
        )
    image_1920 = fields.Image()
