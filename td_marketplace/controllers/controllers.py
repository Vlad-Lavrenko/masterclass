from odoo import http, SUPERUSER_ID
from odoo.http import request
from odoo.tools.image import image_data_uri
import base64

class ConnectorController(http.Controller):

    @http.route('/product/image/<string:type_id>/<int:product_id>/<string:file_name>', type='http', auth='public', methods=['GET'], csrf=False)
    def get_product_image(self, type_id, product_id, file_name, **kwargs):

        if type_id == 'product':
            product = request.env['product.product'].with_user(SUPERUSER_ID).browse(product_id)
            if product:
                image = product.image_1024
                data_uri = image_data_uri(image)
                base64_image = data_uri.split(',')[1] 
                mime_type = data_uri.split(';base64')[0].split('data:')[1]
                image_data = base64.b64decode(image)
                if base64_image:
                    return request.make_response(image_data, headers=[('Content-Type', mime_type)])
                    
        elif type_id == 'template':            
            product = request.env['product.template'].with_user(SUPERUSER_ID).browse(product_id)
            if product:
                image = product.image_1024
                data_uri = image_data_uri(image)
                base64_image = data_uri.split(',')[1] 
                mime_type = data_uri.split(';base64')[0].split('data:')[1]
                image_data = base64.b64decode(image)
                if base64_image:
                    return request.make_response(image_data, headers=[('Content-Type', mime_type)])

        elif type_id == 'product_image':            
            product_image = request.env['product.image'].with_user(SUPERUSER_ID).browse(product_id)
            if product_image:
                image = product_image.image_1024
                data_uri = image_data_uri(image)
                base64_image = data_uri.split(',')[1] 
                mime_type = data_uri.split(';base64')[0].split('data:')[1]
                image_data = base64.b64decode(image)
                if base64_image:
                    return request.make_response(image_data, headers=[('Content-Type', mime_type)])

