import json
import requests
import logging
from odoo import exceptions, _
from odoo.http import request

_logger = logging.getLogger(__name__)

class Opencart:

    def __init__(self, env=False):
        if env != False:
            self.env = env
            self.is_log_enabled = bool(self.env['ir.config_parameter'].sudo().get_param('td_marketplace.mc_use_logging'))
        else:
            self.env = request.env
            self.is_log_enabled = bool(request.env['ir.config_parameter'].sudo().get_param('td_marketplace.mc_use_logging'))

    def request(self, marketplace_id=None, url='', method='post', calledMethod='', data=None, params=None, headers=None):
        # url = f"{server}/api/{calledMethod}"        

        log = False

        if self.is_log_enabled:
            try:
                log = self.env['td.marketplace.log'].sudo().create({
                    'marketplace_id': marketplace_id, 
                    'name': url, 
                    'method': method, 
                    'headers': headers,
                    'called_method': calledMethod,
                    'json': json.dumps(data, indent=2, ensure_ascii=False),
                    'params': json.dumps(params),
                })
            except Exception as e:
                _logger.debug(e)
                _logger.info(e)
            else:
                self.env.cr.commit()

        try:
            response = requests.request(
                method=method, url=url, json=data, params=params,
                headers=headers, timeout=60)
        except Exception as e:   
            if log:
                log.write({'error': e})
                self.env.cr.commit()

            raise exceptions.ValidationError(
                _('Marketplace Connector error: "{}"').format(e))

        if response.status_code == 200:
            res = response.json()

            if log:
                log.write({
                    'code': response.status_code,
                    'response': json.dumps(res, indent=2, ensure_ascii=False),
                    'response_headers': response.headers,
                })
                self.env.cr.commit()
                
            return res

        if log:
            log.write({
                'code': response.status_code, 
                'response': response.text,
                'error': response.text})
            self.env.cr.commit()

        raise exceptions.ValidationError(
            _('Marketplace Connector error: "{}"').format(response.text))
