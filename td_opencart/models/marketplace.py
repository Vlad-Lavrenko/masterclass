from odoo import api, fields, models, _
import requests
import re
import email.utils
from datetime import datetime, timezone, timedelta
from odoo.exceptions import UserError
from odoo.tools.image import image_data_uri
from odoo.tools import float_is_zero

import logging
import urllib3

from .opencart_rest import Opencart

_logger = logging.getLogger('-= Marketplace OPENCART')

class Marketplace(models.Model):
    _inherit = 'td.marketplace'

    code = fields.Selection(
            selection_add=[('opencart', 'opencart')],
            ondelete={'opencart': 'cascade'},                            
        )

    @api.model_create_multi
    def create(self, vals_list):
        marketplaces = super().create(vals_list)        
        return marketplaces        

    def opencart_load_settings(self):
        if not self.use_api:
            raise UserError(_('Exchange works only using API'))

        if not self.api_url:
            raise UserError(_('API url not defined'))

        oc_session_id = self._get_token()
        if oc_session_id:
            url =  self.api_url + '/index.php?route=api/odooConnector/getSettings'
            url = url + '&api_token=' + oc_session_id

            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) CustomClient/1.0',
            }            

            request_result = requests.post(url=url, headers=headers)
            if request_result.status_code == 200:
                answer = request_result.json()
                res = answer.get('result')
                if res=='ok':
                    data = answer.get('data')

                    name = data.get('currency')
                    self.currency_id = self.env['res.currency'].search(domain=[('name','=',name)])

                    name = data.get('language')
                    name = name.replace('-','_')
                    name = name[:2].lower() + name[2:-2] + name[-2:].upper()
                    self.language_id = self.env['res.lang'].search(domain=[('code','=',name)])

                    uoms = data.get('dimension_uom',[])
                    for uom in uoms:
                        name = uom['code']
                        uom_id = self.env['uom.uom'].with_context(lang=uom['lang_locale']).search(domain=[('name','=',name)])    
                        if uom_id:
                            self.dimension_uom = uom_id
                            break

                    uoms = data.get('weight_uom',[])
                    for uom in uoms:
                        name = uom['code']
                        uom_id = self.env['uom.uom'].with_context(lang=uom['lang_locale']).search(domain=[('name','=',name)])    
                        if uom_id:
                            self.weght_uom = uom_id
                            break


    def opencart_load_language(self):
        if not self.use_api:
            raise UserError(_('Exchange works only using API'))

        if not self.api_url:
            raise UserError(_('API url not defined'))

        oc_session_id = self._get_token()
        if oc_session_id:
            url =  self.api_url + '/index.php?route=api/odooConnector/getLanguages'
            url = url + '&api_token=' + oc_session_id

            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) CustomClient/1.0',
            }            

            request_result = requests.post(url=url, headers=headers)
            if request_result.status_code == 200:
                answer = request_result.json()
                res = answer.get('result')
                if res=='ok':
                    datas = answer.get('data')
                    for data in datas:
                        language_id = self.env['td.marketplace.language'].search(domain=[('marketplace_id','=',self.id), ('language_code','=',data['local'])])
                        if not language_id:
                            language_id = self.env['td.marketplace.language'].create({
                                                                                        'marketplace_id': self.id, 
                                                                                        'language_code': data['local'], 
                                                                                        'marketplace_code': data['language_id']
                                                                                    })
                        else:
                            language_id.write({'marketplace_code': data['language_id']})

    def opencart_load_category(self):

        if not self.use_api:
            raise UserError(_('Exchange works only using API'))

        if not self.api_url:
            raise UserError(_('API url not defined'))

        oc_session_id = self._get_token()
        if oc_session_id:
            url =  self.api_url + '/index.php?route=api/odooConnector/getCategories'
            url = url + '&api_token=' + oc_session_id

            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) CustomClient/1.0',
            }            

            request_result = requests.post(url=url,headers=headers)
            if request_result.status_code == 200:
                answer = request_result.json()
                res = answer.get('result')
                if res=='ok':
                    categories = answer.get('data')
                    categories_code = []
                    for category in categories:

                        category_id = self.env['td.marketplace.category'].search(domain=[('marketplace_id','=',self.id), ('code','=',category['category_id'])])
                        if not category_id:
                            category_id = self.env['td.marketplace.category'].create({
                                            'marketplace_id': self.id,
                                            'name': category['name'],
                                            'code': category['category_id'],
                                        })
                            categories_code.append({
                                            'code': int(category['category_id']),
                                            'id': category_id,
                                        })

                            if int(category['parent_id']) != 0:
                                parent_id = next((item for item in categories_code if item['code'] == int(category['parent_id'])), None)
                                if parent_id:
                                    category_id.parent_id = parent_id['id']

                            category_id.compute_full_name()
                        
        return True

    def opencart_load_product(self):
        if not self.use_api:
            raise UserError(_('Exchange works only using API'))

        if not self.api_url:
            raise UserError(_('API url not defined'))

        action = self.env.ref('td_marketplace.td_data_import_wizard_from_marketplace_act_window')    
        action['context'] = {
                                'default_marketplace_id': self.id,
                                'default_procedure': 'opencart_import_product',
                                'default_procedure_description': 'Import product',
                            }        
        
        return action.read()[0]    

    def opencart_import_product(self, page = 1, per_page = 50, do_update = False, site_id = 0):
        _use_logging = (self.env['ir.config_parameter'].sudo().get_param('td_marketplace.mc_use_logging') == 'True')
        self._add_log(_use_logging, _logger, 'Import products')

        oc_session_id = self._get_token()
        if oc_session_id:

            url =  self.api_url + '/index.php?route=api/odooConnector/getProducts'
            url = url + '&api_token=' + oc_session_id

            if site_id != 0:
                json_data={
                    'id': site_id,
                    }
            else:
                json_data={
                    'page': page,
                    'per_page': per_page,
                    }
                    
            headers = {
                        'Content-Type': 'application/json',
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) CustomClient/1.0',
                    } 

            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)        
            request_result = requests.post(url=url, headers=headers, json=json_data, verify=False)

            if request_result.status_code == 200:
                answer = request_result.json()
                res = answer.get('result')
                if res=='ok':
                    datas = answer.get('data')

                    if len(datas)==0:
                        self._add_log(_use_logging, _logger, 'End import products. No more products.')
                        return False
                    else:    
                        self._add_log(_use_logging, _logger, 'Page: ' + f'{page}' + '. Count products to proceed: ' + f'{len(datas)}')

                    languages = self.env['res.lang'].search(domain=[('active','=', True)]).mapped('code')    

                    languages_codes = self.env['td.marketplace.language'].search(domain=[('marketplace_id','=',self.id)]).mapped('language_code')    
                    q_filter_option_name_tmpl = " OR ".join([f"pav.name->>'{lc}'='%value%'" for lc in languages_codes])

                    regular_price_list_id = self.env['td.marketplace.pricelist'].search(domain=[('marketplace_id','=',self.id), ('pricelist_type','=','regular')]).pricelist_id

                    count = 0
                    for data in datas:
                        count+=1

                        product_tmpl_id = False
                        is_new_product = False

                        oc_type = data['type']

                        prod_id = data['id']
                        prod_descr = data['description']

                        mp_offer_id = self.env['td.offer'].search(domain=[('marketplace_id','=',self.id), ('marketplace_code','=',prod_id)])
                        if mp_offer_id:
                            product_tmpl_id = mp_offer_id.product_tmpl_id.with_context(no_update_offer_state=True)

                        # if 'description' in data:
                        if not product_tmpl_id:
                            # prod_descr = data['description']
                            for descr in prod_descr:
                                product_name = self._correcting_name(descr['name'])
                                if product_name:
                                    product_tmpl_id = self.env['product.template'].with_context(lang=descr['lang_locale'], no_update_offer_state=True).search(domain=[('name','=',product_name)], limit=1)
                                    if product_tmpl_id:
                                        break
                        # else:
                        #     return False            

                        if not product_tmpl_id:
                            default_description = next((item for item in prod_descr if item['lang_locale'] == self.language_id.code), None)
                            if default_description:
                                t_name = self._correcting_name(default_description['name'])
                                product_tmpl_id = self.env['product.template'].with_context(no_update_offer_state=True).create({
                                        'name': t_name,
                                        'type':'product',
                                    })   
                                product_name = t_name    
                            else:
                                product_tmpl_id = self.env['product.template'].with_context(no_update_offer_state=True).create({
                                        'name': 'opencart_product',
                                        'type':'product',
                                    })   
                                product_name = 'opencart_product'    

                            is_new_product = True  
                            self._add_log(_use_logging, _logger, f'{count}' + '. Create product: ' + f'{product_name}')
                
                        if is_new_product or ( not is_new_product and do_update ):  
                            
                            if not is_new_product:
                                self._add_log(_use_logging, _logger, f'{count}' + '. Update product: ' + f'{product_tmpl_id.id}')
                                product_tmpl_id.ensure_one()

                            mp_product_field_id = self.env['td.marketplace.product.field'].with_context(no_update_offer_state=True).search(domain=[('marketplace_id','=',self.id),('product_tmpl_id','=',product_tmpl_id.id)])    
                            if not mp_product_field_id:
                                mp_product_field_id = self.env['td.marketplace.product.field'].with_context(no_update_offer_state=True).create({'marketplace_id':self.id, 'product_tmpl_id':product_tmpl_id.id})

                            if data['date_available'] and data['date_available'] != '0000-00-00':   
                                t_date =  (data['date_available'] + ' 00:00:00')[:19]
                                mp_product_field_id.oc_date_available = datetime.strptime(t_date, '%Y-%m-%d %H:%M:%S')

                            default_description = next((item for item in prod_descr if item['lang_locale'] == self.language_id.code), None)
                            if default_description:
                                t_descr_def = self._correcting_name(default_description['description'])
                                t_name_def = self._correcting_name(default_description['name'])
                                product_tmpl_id.write({
                                        'name': t_name_def,
                                        'description': t_descr_def,
                                    })
                            else:        
                                t_descr_def = ''
                                t_name_def = ''

                            for languge in languages:
                                t_description = next((item for item in prod_descr if item['lang_locale'] == languge), None)
                                t_name_upd = ''
                                t_descr_upd = ''
                                if t_description:
                                    t_name = self._correcting_name(t_description['name'])
                                    if not t_name:
                                        t_name_upd = t_name_def
                                    else:    
                                        t_name_upd = t_name
                                    t_descr = self._correcting_name(t_description['description'])
                                    if not t_descr:
                                        t_descr_upd = t_descr_def
                                    else:    
                                        t_descr_upd = t_descr    
                                    t_tag = t_description['tag']
                                    t_meta_title = t_description['meta_title']
                                    t_meta_description = t_description['meta_description']
                                    t_meta_keyword = t_description['meta_keyword']
                                else:        
                                    t_name = ''
                                    t_descr = ''
                                    t_name_upd = t_name_def
                                    t_descr_upd = t_descr_def
                                    t_tag = ''
                                    t_meta_title = ''
                                    t_meta_description = ''
                                    t_meta_keyword = ''

                                prev_name = product_tmpl_id.with_context(lang=languge).name
                                if (prev_name and prev_name != t_name_upd and t_name) or (not prev_name):
                                    product_tmpl_id.with_context(lang=languge).name = t_name_upd

                                prev_descr = product_tmpl_id.with_context(lang=languge).description
                                if (prev_descr and prev_descr != t_descr_upd and t_descr) or (not prev_descr):
                                    product_tmpl_id.with_context(lang=languge).description = t_descr_upd

                                mp_product_field_id.with_context(no_update_offer_state=True, lang=languge).write({
                                        'oc_tag': t_tag,
                                        'oc_meta_title': t_meta_title,
                                        'oc_meta_description': t_meta_description,
                                        'oc_meta_keywords': t_meta_keyword,
                                    })    

                            self._opencart_import_product_extend(product_tmpl_id, data)

                            oc_prod_seo = data['seo']        
                            for seo in oc_prod_seo:
                                mp_product_field_id.with_context(lang=seo['lang_locale']).write({
                                        'oc_seo_url': seo['keyword'],  
                                    })    

                            oc_manufacturer = data.get('manufacturer')
                            if oc_manufacturer:
                                manufacturer_id = self.env['td.manufacturer'].search(domain=[('name','=',oc_manufacturer['name'])])
                                if not manufacturer_id:
                                    manufacturer_id = self.env['td.manufacturer'].create({'name': oc_manufacturer['name']})
                                    for descr in oc_manufacturer['description']:
                                        manufacturer_id.with_context(lang=descr['lang_locale']).write({
                                                                        'description': descr['description']   
                                                                    })

                                product_tmpl_id.td_manufacturer_id = manufacturer_id.id

                            product_tmpl_id.default_code = data['model']
                            product_tmpl_id.td_weight = float(data['weight'])
                            product_tmpl_id.td_length = float(data['length'])
                            product_tmpl_id.td_width = float(data['width'])
                            product_tmpl_id.td_height = float(data['height'])

                            if 'weight_uom' in data:
                                weight_uom = data['weight_uom']
                                for descr in weight_uom:
                                    uom_code = self._correcting_name(descr['code'])
                                    uom_id = self.env['uom.uom'].search(domain=[('name','=',uom_code)])    
                                    if uom_id:
                                        product_tmpl_id.td_uom_weight = uom_id
                                        break

                            if 'dimension_uom' in data:
                                dimension_uom = data['dimension_uom']
                                for descr in dimension_uom:
                                    uom_code = self._correcting_name(descr['code'])
                                    uom_id = self.env['uom.uom'].search(domain=[('name','=',uom_code)])    
                                    if uom_id:
                                        product_tmpl_id.td_uom_dimension = uom_id
                                        break

                            if 'image' in data:    
                                base64_image = data['image'].split(',')[1]  
                                product_tmpl_id.image_1920 = base64_image

                            if 'images' in data:
                                product_image_ids = self.env['product.image'].search(domain=[('product_tmpl_id','=',product_tmpl_id.id)])
                                product_image_ids.unlink()

                                for image in data['images']:

                                    product_image_id = self.env['product.image'].search(domain=[
                                                                                    ('product_tmpl_id','=',product_tmpl_id.id),
                                                                                    ('name','=',image['name']),
                                                                                ])
                                    if not product_image_id:                                                                                        
                                        base64_image = image['image'].split(',')[1]
                                        product_image_id = self.env['product.image'].create({
                                                                'product_tmpl_id': product_tmpl_id.id,
                                                                'image_1920': base64_image,
                                                                'name': image['name'],
                                                                'sequence': image['order'],
                                                            })

                            for attribute in data['attribute']:
                                attribute_id = False
                                marketplace_attribute_id = self.env['td.marketplace.attribute'].search(domain=[('marketplace_id','=', self.id), 
                                                                                                                ('marketplace_code','=',int(attribute['attribute_id'])),
                                                                                                                ('prefix','=','atr')
                                                                                                            ])

                                if marketplace_attribute_id:
                                    attribute_id = marketplace_attribute_id.attribute_id
                                    if attribute_id:
                                        values_ids = []
                                        attribute_value_id = False

                                        for attribute_value in attribute['value']:
                                            if not attribute_value['text']:
                                                continue
                                            attribute_value_id = self.env['product.attribute.value'].with_context(lang=attribute_value['lang_locale']).search(domain=[('attribute_id','=',attribute_id.id), ('name','=',attribute_value['text'])], limit=1)
                                            if attribute_value_id:
                                                break
                                        if not attribute_value_id:
                                            attribute_value_id = self.env['product.attribute.value'].create({
                                                                                                            'attribute_id': attribute_id.id,
                                                                                                            'name': 'opencart_value',
                                                                                                        })
                                            for attribute_value in attribute['value']:
                                                if not attribute_value['text']:
                                                    continue
                                                attribute_value_id.with_context(lang=attribute_value['lang_locale']).write({
                                                        'name': attribute_value['text'],
                                                    })

                                        values_ids.append(attribute_value_id.id)

                                        td_make_variant = False            

                                        prod_tmpl_attr_line_id = self.env['product.template.attribute.line'].with_context(no_update_offer_state=True).search(domain=[('product_tmpl_id','=',product_tmpl_id.id), ('attribute_id','=',attribute_id.id)])           
                                        if not prod_tmpl_attr_line_id:
                                            prod_tmpl_attr_line_id = self.env['product.template.attribute.line'].with_context(no_update_offer_state=True).create({
                                                                                                                        'product_tmpl_id': product_tmpl_id.id,
                                                                                                                        'attribute_id': attribute_id.id,
                                                                                                                        'td_make_variant': td_make_variant,
                                                                                                                        'value_ids': [(6,0,[attribute_value_id.id])]
                                                                                                                })
                                        else:
                                            prod_tmpl_attr_line_id.td_make_variant = td_make_variant
                                            ptav_id = self.env['product.template.attribute.value'].with_context(no_update_offer_state=True).search(domain=[
                                                                                                                    ('product_tmpl_id', '=', product_tmpl_id.id),
                                                                                                                    ('attribute_line_id', '=', prod_tmpl_attr_line_id.id),
                                                                                                                    ('attribute_id', '=', attribute_id.id),
                                                                                                                    ('product_attribute_value_id', '=', attribute_value_id.id),
                                                                                                                ])
                                            if not ptav_id:
                                                values_ids = prod_tmpl_attr_line_id.value_ids.mapped('id') + values_ids
                                                prod_tmpl_attr_line_id.write({
                                                                                'value_ids': [(6,0,values_ids)]
                                                                            })
                            # product options
                            for option in data['option']:
                                attribute_id = False
                                marketplace_attribute_id = self.env['td.marketplace.attribute'].search(domain=[('marketplace_id','=', self.id), 
                                                                                                                ('marketplace_code','=',int(option['option_id'])),
                                                                                                                ('prefix','=','opt')
                                                                                                            ])
                                if marketplace_attribute_id:
                                    attribute_id = marketplace_attribute_id.attribute_id

                                    if attribute_id:
                                        attribute_value_id = False
                                        values_ids = []
                                        for value in option['values']:
                                            attribute_value_id = False

                                            for attribute_value in value['value']:
                                                attribute_value_id = self.env['product.attribute.value'].with_context(lang=attribute_value['lang_locale'], no_update_offer_state=True).search(domain=[('attribute_id','=',attribute_id.id), ('name','=',attribute_value['name'])])
                                                if attribute_value_id:
                                                    break
                                            if not attribute_value_id:
                                                attribute_value_id = self.env['product.attribute.value'].with_context(no_update_offer_state=True).create({
                                                                                                                'attribute_id': attribute_id.id,
                                                                                                                'name': 'opencart_value',
                                                                                                            })
                                                for attribute_value in value['value']:
                                                    attribute_value_id.with_context(lang=attribute_value['lang_locale']).write({
                                                            'name': attribute_value['name'],
                                                        })

                                            values_ids.append(attribute_value_id.id)

                                        if oc_type == 'variable':
                                            td_make_variant = True
                                        else:     
                                            td_make_variant = False                                            

                                        prod_tmpl_attr_line_id = self.env['product.template.attribute.line'].with_context(no_update_offer_state=True).search(domain=[('product_tmpl_id','=',product_tmpl_id.id), ('attribute_id','=',attribute_id.id)])           
                                        if not prod_tmpl_attr_line_id:
                                            # TODO if attribute in odu make variants product and on site no variants...
                                            prod_tmpl_attr_line_id = self.env['product.template.attribute.line'].with_context(no_update_offer_state=True).create({
                                                                                                                        'product_tmpl_id': product_tmpl_id.id,
                                                                                                                        'attribute_id': attribute_id.id,
                                                                                                                        'td_make_variant': td_make_variant,
                                                                                                                        'value_ids': [(6,0,values_ids)]
                                                                                                                })
                                        else:
                                            prod_tmpl_attr_line_id.td_make_variant = td_make_variant
                                            ptav_id = self.env['product.template.attribute.value'].with_context(no_update_offer_state=True).search(domain=[
                                                                                                                    ('product_tmpl_id', '=', product_tmpl_id.id),
                                                                                                                    ('attribute_line_id', '=', prod_tmpl_attr_line_id.id),
                                                                                                                    ('attribute_id', '=', attribute_id.id),
                                                                                                                    ('product_attribute_value_id', '=', attribute_value_id.id),
                                                                                                                ])
                                            if not ptav_id:
                                                prod_tmpl_attr_line_id.write({
                                                                                'value_ids': [(6,0,values_ids)]
                                                                            })
                        # NOTE do commit before update offer 

                        oc_category_id = int(data.get('category',0))
                        if oc_category_id:
                            category_id = self.env['td.marketplace.category'].search(domain=[('marketplace_id','=',self.id), ('code','=',oc_category_id)])
                            if category_id:
                                mp_cat_prod_id = self.env['td.marketplace.category.product'].search(domain=[('marketplace_id','=',self.id), ('product_tmpl_id','=',product_tmpl_id.id), ('category_id','=',category_id.id)],)
                                if not mp_cat_prod_id:
                                    self.env['td.marketplace.category.product'].with_context(no_update_offer_state=True).create({
                                                                                        'marketplace_id': self.id,
                                                                                        'product_tmpl_id': product_tmpl_id.id,
                                                                                        'category_id': category_id.id,
                                                                                        })

                        self.env.cr.commit()

                        if oc_type == 'simple' and product_tmpl_id.product_variant_count >= 1:
                            if product_tmpl_id.product_variant_count == 1:
                                product_id = product_tmpl_id.product_variant_id    

                                offer_id = self.env['td.offer'].search(domain=[('marketplace_id','=',self.id), ('product_id','=',product_id.id)])
                                if not offer_id:
                                    offer_id = self.env['td.offer'].create({
                                            'product_id': product_id.id,
                                            'marketplace_id': self.id,
                                            'state': 'processed',
                                            'marketplace_code': data['id'],
                                            'marketplace_variant_code': '',
                                        }) 
                                else:
                                    offer_id.write({'state': 'processed'})
                            else:        
                                offer_id = self.env['td.offer'].search(domain=[('marketplace_id','=',self.id), ('product_tmpl_id','=',product_tmpl_id.id)]).unlink()
                                for product_variant_id in product_tmpl_id.product_variant_ids: 
                                    offer_id = self.env['td.offer'].create({
                                                'product_id': product_variant_id.id,
                                                'marketplace_id': self.id,
                                                'marketplace_code': data['id'],
                                                'marketplace_variant_code': '',
                                                'state': 'to_process',
                                            }) 

                            price = float(data['price'] if data['price'] else '0.00') 
                            
                            if not float_is_zero(price, precision_digits=3) and regular_price_list_id and do_update:
                                price_list_item_id = self.env['product.pricelist.item'].with_context(no_update_offer_state=True).search(domain=[
                                                                                                        ('pricelist_id','=',regular_price_list_id.id),
                                                                                                        ('product_tmpl_id','=',product_tmpl_id.id),
                                                                                                        ('product_id','=',None)
                                                                                                    ])
                                if price_list_item_id:
                                    price_list_item_id.fixed_price = price
                                else:
                                    self.env['product.pricelist.item'].with_context(no_update_offer_state=True).create({
                                                                                'pricelist_id': regular_price_list_id.id,
                                                                                'company_id': regular_price_list_id.company_id.id,
                                                                                'currency_id': regular_price_list_id.currency_id.id,
                                                                                'product_tmpl_id': product_tmpl_id.id,
                                                                                'product_id': None,
                                                                                'applied_on': '1_product',
                                                                                'base': 'list_price',
                                                                                'compute_price': 'fixed',
                                                                                'fixed_price': price,
                                                                            })    

                            self.env.cr.commit()

                        elif oc_type == 'simple' and product_tmpl_id.product_variant_count > 1:
                            product_id = product_tmpl_id.product_variant_id                                
                            offer_id = self.env['td.offer'].search(domain=[('marketplace_id','=',self.id), ('product_id','=',product_id.id)])
                            if not offer_id:
                                offer_id = self.env['td.offer'].create({
                                        'product_id': product_id.id,
                                        'marketplace_id': self.id,
                                        'state': 'processed',
                                        'marketplace_code': data['id'],
                                        'marketplace_variant_code': '',
                                    }) 
                            else:
                                offer_id.write({'state': 'processed'})

                            self.env.cr.commit()
                            
                        elif oc_type == 'variable' and product_tmpl_id.product_variant_count > 0:
                            price = float(data['price'] if data['price'] else '0.00') 

                            if not float_is_zero(price, precision_digits=3) and regular_price_list_id and do_update:
                                price_list_item_id = self.env['product.pricelist.item'].with_context(no_update_offer_state=True).search(domain=[
                                                                                                        ('pricelist_id','=',regular_price_list_id.id),
                                                                                                        ('product_tmpl_id','=',product_tmpl_id.id),
                                                                                                        ('product_id','=',None)
                                                                                                    ])
                                if price_list_item_id:
                                    price_list_item_id.fixed_price = price
                                else:
                                    self.env['product.pricelist.item'].with_context(no_update_offer_state=True).create({
                                                                                'pricelist_id': regular_price_list_id.id,
                                                                                'company_id': regular_price_list_id.company_id.id,
                                                                                'currency_id': regular_price_list_id.currency_id.id,
                                                                                'product_tmpl_id': product_tmpl_id.id,
                                                                                'product_id': None,
                                                                                'applied_on': '1_product',
                                                                                'base': 'list_price',
                                                                                'compute_price': 'fixed',
                                                                                'fixed_price': price,
                                                                            })    

                            oc_options = data['option']
                            for oc_option in oc_options:
                                for oc_variant in oc_option['values']:
                                    product_id = self._oc_get_product_by_variant(product_tmpl_id, oc_option['option_id'], oc_variant, q_filter_option_name_tmpl)    
                                    if product_id:
                                        offer_id = self.env['td.offer'].search(domain=[('marketplace_id','=',self.id), ('product_id','=',product_id.id)])
                                        if not offer_id:
                                            offer_id = self.env['td.offer'].create({
                                                    'product_id': product_id.id,
                                                    'marketplace_id': self.id,
                                                    'state': 'processed',
                                                    'marketplace_code': data['id'],
                                                    'marketplace_variant_code': oc_variant['variant'],
                                                }) 
                                        else:
                                            offer_id.write({'state': 'processed',
                                                            'marketplace_code': data['id'],
                                                            'marketplace_variant_code': oc_variant['variant'],
                                            })

                                        price = float(oc_variant.get('price', '0.00'))
                                        sign = oc_variant.get('price_sign', '+')
                                        product_price = float(data['price'])

                                        if not float_is_zero(price, precision_digits=3):
                                            if sign == '-':
                                                variant_price = product_price - price
                                            else:
                                                variant_price = product_price + price

                                            if not float_is_zero(variant_price, precision_digits=3) and regular_price_list_id and do_update:
                                                price_list_item_id = self.env['product.pricelist.item'].with_context(no_update_offer_state=True).search(domain=[
                                                                                                                        ('pricelist_id','=',regular_price_list_id.id),
                                                                                                                        ('product_tmpl_id','=',product_tmpl_id.id),
                                                                                                                        ('product_id','=',product_id.id)
                                                                                                                    ])
                                                if price_list_item_id:
                                                    price_list_item_id.fixed_price = variant_price
                                                else:
                                                    self.env['product.pricelist.item'].with_context(no_update_offer_state=True).create({
                                                                                                'pricelist_id': regular_price_list_id.id,
                                                                                                'company_id': regular_price_list_id.company_id.id,
                                                                                                'currency_id': regular_price_list_id.currency_id.id,
                                                                                                'product_tmpl_id': product_tmpl_id.id,
                                                                                                'product_id': product_id.id,
                                                                                                'applied_on': '0_product_variant',
                                                                                                'base': 'list_price',
                                                                                                'compute_price': 'fixed',
                                                                                                'fixed_price': variant_price,
                                                                                            })    
                                        weight = float(oc_variant.get('weight', '0.00'))
                                        sign = oc_variant.get('weight_sign', '+')
                                        product_weight = float(data['weight'])

                                        if not float_is_zero(weight, precision_digits=3):
                                            if sign == '-':
                                                variant_weight = product_weight - weight
                                            else:
                                                variant_weight = product_weight + weight
                                            product_id.td_weight = variant_weight
                                            product_id.td_uom_weight = product_tmpl_id.td_uom_weight

                            self.env.cr.commit()
                        # discount: price_list for each discount group
                        oc_discounts = data.get('discount',[])
                        for oc_discount in oc_discounts:
                            sale_price_list = self.env['td.marketplace.pricelist'].search(domain=[('marketplace_id','=',self.id), ('marketplace_code','=',oc_discount['id']), ('pricelist_type','=','sale')]).pricelist_id
                            if sale_price_list:
                                price_list_item_id = self.env['product.pricelist.item'].with_context(no_update_offer_state=True).search(domain=[
                                                                                                        ('pricelist_id','=',sale_price_list.id),
                                                                                                        ('product_tmpl_id','=',product_tmpl_id.id),
                                                                                                        ('product_id','=',None)
                                                                                                    ])
                                if price_list_item_id:
                                    price_list_item_id.fixed_price = oc_discount['price']
                                    price_list_item_id.min_quantity = oc_discount['min_quantity']
                                    price_list_item_id.date_start = oc_discount['date_start'] if oc_discount['date_start'] != '0000-00-00' else False
                                    price_list_item_id.date_end = oc_discount['date_end'] if oc_discount['date_end'] != '0000-00-00' else False
                                else:
                                    self.env['product.pricelist.item'].with_context(no_update_offer_state=True).create({
                                                                                'pricelist_id': sale_price_list.id,
                                                                                'company_id': sale_price_list.company_id.id,
                                                                                'currency_id': sale_price_list.currency_id.id,
                                                                                'product_tmpl_id': product_tmpl_id.id,
                                                                                'product_id': None,
                                                                                'applied_on': '1_product',
                                                                                'base': 'list_price',
                                                                                'compute_price': 'fixed',
                                                                                'fixed_price': oc_discount['price'],
                                                                                'min_quantity': oc_discount['min_quantity'],
                                                                                'date_start': oc_discount['date_start'] if oc_discount['date_start'] != '0000-00-00' else False,
                                                                                'date_end': oc_discount['date_end'] if oc_discount['date_end'] != '0000-00-00' else False,
                                                                            })    

                        # promotion: price_list for each promotion group
                        oc_promotions = data.get('promotion',[])
                        for oc_promotion in oc_promotions:
                            promo_price_list = self.env['td.marketplace.pricelist'].search(domain=[('marketplace_id','=',self.id), ('marketplace_code','=',oc_promotion['id']), ('pricelist_type','=','promotion')]).pricelist_id
                            if promo_price_list:
                                price_list_item_id = self.env['product.pricelist.item'].with_context(no_update_offer_state=True).search(domain=[
                                                                                                        ('pricelist_id','=',promo_price_list.id),
                                                                                                        ('product_tmpl_id','=',product_tmpl_id.id),
                                                                                                        ('product_id','=',None)
                                                                                                    ])
                                if price_list_item_id:
                                    price_list_item_id.fixed_price = oc_promotion['price']
                                    price_list_item_id.min_quantity = 1
                                    price_list_item_id.date_start = oc_promotion['date_start'] if oc_promotion['date_start'] != '0000-00-00' else False
                                    price_list_item_id.date_end = oc_promotion['date_end'] if oc_promotion['date_end'] != '0000-00-00' else False
                                else:
                                    self.env['product.pricelist.item'].with_context(no_update_offer_state=True).create({
                                                                                'pricelist_id': promo_price_list.id,
                                                                                'company_id': promo_price_list.company_id.id,
                                                                                'currency_id': promo_price_list.currency_id.id,
                                                                                'product_tmpl_id': product_tmpl_id.id,
                                                                                'product_id': None,
                                                                                'applied_on': '1_product',
                                                                                'base': 'list_price',
                                                                                'compute_price': 'fixed',
                                                                                'fixed_price': oc_promotion['price'],
                                                                                'min_quantity': 1,
                                                                                'date_start': oc_promotion['date_start'] if oc_promotion['date_start'] != '0000-00-00' else False,
                                                                                'date_end': oc_promotion['date_end'] if oc_promotion['date_end'] != '0000-00-00' else False,
                                                                            })    
                        self.env.cr.commit()

            self._add_log(_use_logging, _logger, 'End import products.')
            return True

    def _opencart_import_product_extend(self, product_tmpl_id, data):
        return True

    def opencart_load_attribute(self):
        if not self.use_api:
            raise UserError(_('Exchange works only using API'))

        if not self.api_url:
            raise UserError(_('API url not defined'))

        oc_session_id = self._get_token()
        if oc_session_id:
            url = self.api_url + '/index.php?route=api/odooConnector/getAttributes'
            url = url + '&api_token=' + oc_session_id

            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) CustomClient/1.0',
            }            

            request_result = requests.post(url=url, headers=headers)
            if request_result.status_code == 200:
                answer = request_result.json()
                res = answer.get('result')
                if res=='ok':
                    datas = answer.get('data')
                    for data in datas:
                        if 'description' in data:
                            attr_descr = data['description']
                            attribute_id = False
                            for descr in attr_descr:
                                c_name = self._correcting_name(descr['name'])
                                attribute_id = self.env['product.attribute'].with_context(lang=descr['lang_locale']).search(domain=[('name','=',c_name)], limit=1)
                                if attribute_id:
                                    break
                            if not attribute_id:
                                attribute_id = self.env['product.attribute'].create({
                                        'name': 'opencart_product_attribute',
                                        'create_variant': 'no_variant'
                                    })  
                                for descr in attr_descr:
                                    c_name = self._correcting_name(descr['name'])
                                    attribute_id.with_context(lang=descr['lang_locale']).write({
                                            'name': c_name,
                                        })

                            marketplace_attribute_id = self.env['td.marketplace.attribute'].search(domain=[('marketplace_id','=', self.id), ('attribute_id','=',attribute_id.id), ('prefix','=','atr')])
                            if not marketplace_attribute_id:
                                self.env['td.marketplace.attribute'].create({
                                                'marketplace_id': self.id,
                                                'attribute_id': attribute_id.id,
                                                'marketplace_code': data['attribute_id'],
                                                'prefix': 'atr',
                                            })            
                            else:
                                marketplace_attribute_id.write({'marketplace_code': data['attribute_id']})

            url = self.api_url + '/index.php?route=api/odooConnector/getOptions'
            url = url + '&api_token=' + oc_session_id

            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) CustomClient/1.0',
            }            

            request_result = requests.post(url=url, headers=headers)
            if request_result.status_code == 200:
                answer = request_result.json()
                res = answer.get('result')
                if res=='ok':
                    datas = answer.get('data')
                    for data in datas:
                        if 'description' in data:
                            opt_descr = data['description']
                            attribute_id = False
                            for descr in opt_descr:                                    
                                c_name = self._correcting_name(descr['name'])
                                attribute_id = self.env['product.attribute'].with_context(lang=descr['lang_locale']).search(domain=[('name','=',c_name)])
                                if attribute_id:
                                    break
                            if not attribute_id:
                                attribute_id = self.env['product.attribute'].create({
                                        'name': 'opencart_product_attribute',
                                        'create_variant': 'no_variant'
                                    })  
                                for descr in opt_descr:
                                    c_name = self._correcting_name(descr['name'])
                                    attribute_id.with_context(lang=descr['lang_locale']).write({
                                            'name': c_name,
                                        })
                            if 'values' in data:
                                opt_values = data['values']
                                for value in opt_values:
                                    if 'description' in value:
                                        opt_val_descr = value['description']
                                        attribute_value_id = False
                                        if opt_val_descr:
                                            for descr in opt_val_descr:
                                                c_name = self._correcting_name(descr['name'])
                                                attribute_value_id = self.env['product.attribute.value'].with_context(lang=descr['lang_locale']).search(domain=[('name','=',c_name), ('attribute_id','=', attribute_id.id)])
                                                if attribute_value_id:
                                                    break
                                            if not attribute_value_id:
                                                attribute_value_id = self.env['product.attribute.value'].create({
                                                        'name': 'opencart_product_attribute',
                                                        'attribute_id': attribute_id.id
                                                    })  
                                                for descr in opt_val_descr:
                                                    c_name = self._correcting_name(descr['name'])
                                                    attribute_value_id.with_context(lang=descr['lang_locale']).write({
                                                            'name': c_name,
                                                        })

                            marketplace_attribute_id = self.env['td.marketplace.attribute'].search(domain=[('marketplace_id','=', self.id), ('attribute_id','=',attribute_id.id), ('prefix','=','opt')])
                            if not marketplace_attribute_id:
                                self.env['td.marketplace.attribute'].create({
                                                'marketplace_id': self.id,
                                                'attribute_id': attribute_id.id,
                                                'marketplace_code': data['option_id'],
                                                'prefix': 'opt',
                                            })            
                            else:
                                marketplace_attribute_id.write({'marketplace_code': data['option_id']})

    def opencart_load_partner(self):
        if not self.use_api:
            raise UserError(_('Exchange works only using API'))

        if not self.api_url:
            raise UserError(_('API url not defined'))

        action = self.env.ref('td_marketplace.td_data_import_wizard_from_marketplace_act_window')    
        action['context'] = {
                                'default_marketplace_id': self.id,
                                'default_procedure': 'opencart_import_partner',
                                'default_procedure_description': 'Import partner',
                            }        
        
        return action.read()[0]    

    def opencart_load_manufacturer(self):
        if not self.use_api:
            raise UserError(_('Exchange works only using API'))

        if not self.api_url:
            raise UserError(_('API url not defined'))

        action = self.env.ref('td_marketplace.td_data_import_wizard_from_marketplace_act_window')    
        action['context'] = {
                                'default_marketplace_id': self.id,
                                'default_procedure': 'opencart_import_manufacturer',
                                'default_procedure_description': 'Import manufacturer',
                            }        
        
        return action.read()[0]    

    def opencart_load_pricelist(self):
        if not self.use_api:
            raise UserError(_('Exchange works only using API'))

        if not self.api_url:
            raise UserError(_('API url not defined'))

        action = self.env.ref('td_marketplace.td_data_import_wizard_from_marketplace_act_window')    
        action['context'] = {
                                'default_marketplace_id': self.id,
                                'default_procedure': 'opencart_import_pricelist',
                                'default_procedure_description': 'Import pricelist',
                            }        
        
        return action.read()[0]    

    def opencart_import_pricelist(self, page = 1, per_page = 50, do_update = False):  
        _use_logging = (self.env['ir.config_parameter'].sudo().get_param('td_marketplace.mc_use_logging') == 'True')
        self._add_log(_use_logging, _logger, 'Import partners')
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)        

        oc_session_id = self._get_token()
        if oc_session_id:

            url =  self.api_url + '/index.php?route=api/odooConnector/getCustomersGroups'
            url = url + '&api_token=' + oc_session_id

            json_data={
                'page': page,
                'per_page': per_page,
                }
            headers = {
                        'Content-Type': 'application/json',
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) CustomClient/1.0',
                    } 

            request_result = requests.post(url=url, headers=headers, json=json_data)
            self._add_log(_use_logging, _logger, 'Ger request ' + f'{url}' + ' Request code: ' + f'{request_result.status_code}')

            if request_result.status_code == 200:
                answer = request_result.json()
                res = answer.get('result')
                if res=='ok':
                    datas = answer.get('data')

                    if len(datas)==0:
                        self._add_log(_use_logging, _logger, 'End import pricelist. No more pricelist.')
                        return False

                    count = 0
                    for data in datas:
                        count+=1
                        if 'description' in data:
                            o_descr = data['description']
                            pricelist_id = False
                            for descr in o_descr:                                    
                                c_name = self._correcting_name(descr['name'])
                                pricelist_id = self.env['product.pricelist'].with_context(lang=descr['lang_locale']).search(domain=[('name','=',c_name)])
                                if pricelist_id:
                                    break
                            if not pricelist_id:
                                currency_id = self.env['res.currency'].search(domain=[('name','=',data['currency'])])    
                                pricelist_id = self.env['product.pricelist'].create({
                                        'name': 'opencart_pricelist',
                                        'currency_id': currency_id.id if currency_id else False,
                                    })  

                                for descr in o_descr:                                    
                                    c_name = self._correcting_name(descr['name'])
                                    pricelist_id.with_context(lang=descr['lang_locale']).write({'name': c_name})

                            mp_pricelist = self.env['td.marketplace.pricelist'].search(domain=[('marketplace_id','=',self.id), ('pricelist_id','=',pricelist_id.id)])
                            if mp_pricelist:
                                mp_pricelist.marketplace_code = data['id']
                            else:
                                self.env['td.marketplace.pricelist'].create({
                                                                            'marketplace_id': self.id,
                                                                            'pricelist_id': pricelist_id.id,
                                                                            'marketplace_code': data['id'],
                                                                            'pricelist_type': 'sale',
                                                                            })

    def opencart_import_partner(self, page = 1, per_page = 50, do_update = False):
        _use_logging = (self.env['ir.config_parameter'].sudo().get_param('td_marketplace.mc_use_logging') == 'True')
        self._add_log(_use_logging, _logger, 'Import partners')
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)        

        oc_session_id = self._get_token()
        if oc_session_id:

            url =  self.api_url + '/index.php?route=api/odooConnector/getCustomers'
            url = url + '&api_token=' + oc_session_id

            json_data={
                'page': page,
                'per_page': per_page,
                }
            headers = {
                        'Content-Type': 'application/json',
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) CustomClient/1.0',
                    } 

            request_result = requests.post(url=url, headers=headers, json=json_data)
            self._add_log(_use_logging, _logger, 'Ger request ' + f'{url}' + ' Request code: ' + f'{request_result.status_code}')

            if request_result.status_code == 200:
                answer = request_result.json()
                res = answer.get('result')
                if res=='ok':
                    datas = answer.get('data')

                    if len(datas)==0:
                        self._add_log(_use_logging, _logger, 'End import partner. No more partner.')
                        return False

                    count = 0
                    for data in datas:
                        count+=1

                        partner_id = self._oc_update_partner(data, do_update)
                        self._add_log(_use_logging, _logger, f'{count}' + '. Update partner: ' + f'{partner_id.name}')

                    self.env.cr.commit()
                    self._add_log(_use_logging, _logger, 'End import partner.')
                    return True

                else:
                    self._add_log(_use_logging, _logger, 'End import partner. No more partner.')
                    return False

    def _oc_update_partner(self, data, do_update):

        partner_id = False

        name = data['firstname'] + ' ' + data['lastname']
        email = data['email']
        phone = data['phone']

        if name.strip() and email.strip() and phone.strip():                       
            partner_id = self.env['res.partner'].search(domain=[('name','=',name), ('email','=',email), ('phone','=',phone)], limit=1)

        if not partner_id and name.strip() and phone.strip():    
            partner_id = self.env['res.partner'].search(domain=[('name','=',name), ('phone','=',phone)], limit=1)

        if not partner_id and name.strip() and email.strip():    
            partner_id = self.env['res.partner'].search(domain=[('name','=',name), ('email','=',email)], limit=1)

        if not partner_id and name.strip() and email.strip():    
            partner_id = self.env['res.partner'].search(domain=[('name','=',name)], limit=1)

        if not partner_id and phone.strip():    
            partner_id = self.env['res.partner'].search(domain=[('phone','=',phone)], limit=1)

        if not partner_id and email.strip():    
            partner_id = self.env['res.partner'].search(domain=[('email','=',email)], limit=1)

        # if not partner_id:
        #     return False

        is_new_partner = False       
        country_id = False
        state_id = False

        if data.get('country_code'):
            country_id = self.env['res.country'].search(domain=[('code','=',data.get('country_code'))])

        if country_id and data.get('zone_name'):
            state_id = self.env['res.country.state'].search(domain=[('country_id','=',country_id.id), ('name','=',data.get('zone_name'))])    

        city = data.get('city')
        street = data.get('address_1')

        if not partner_id:
            c_name = name if name.strip() else email if email.strip() else phone
            partner_id = self.env['res.partner'].create({
                                                        'name': c_name,
                                                        'email': email,
                                                        'phone': phone,
                                                        'country_id': country_id.id if country_id else False,
                                                        'state_id': state_id.id if state_id else False,
                                                        'city': city if city else '',
                                                        'street': street if street else '',
                                                    })
            is_new_partner = True

        if not is_new_partner and do_update:  
            c_name = name if name.strip() else email if email.strip() else phone
            partner_id.write({
                                'name': c_name,
                                'email': email,
                                'phone': phone,
                                'country_id': country_id.id if country_id else False,
                                'state_id': state_id.id if state_id else False,
                                'city': city if city else '',
                                'street': street if street else '',
                })
                        
        mp_partner_id = self.env['td.marketplace.partner'].search(domain=[('marketplace_id','=',self.id), ('partner_id','=',partner_id.id)])
        if not mp_partner_id:
            mp_partner_id = self.env['td.marketplace.partner'].create({
                    'partner_id': partner_id.id,
                    'marketplace_id': self.id,
                    'marketplace_code': data['id'],
                })   
        return partner_id

    def opencart_import_manufacturer(self, page = 1, per_page = 50, do_update = False, site_id=0):
        _use_logging = (self.env['ir.config_parameter'].sudo().get_param('td_marketplace.mc_use_logging') == 'True')
        self._add_log(_use_logging, _logger, 'Import manufacturers')
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)        

        oc_session_id = self._get_token()
        if oc_session_id:
            url =  self.api_url + '/index.php?route=api/odooConnector/getManufacturers'
            url = url + '&api_token=' + oc_session_id

            if site_id != 0:
                json_data={
                    'id': site_id,
                    }
            else:
                json_data={
                    'page': page,
                    'per_page': per_page,
                    }

            headers = {
                        'Content-Type': 'application/json',
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) CustomClient/1.0',
                    } 

            request_result = requests.post(url=url, headers=headers, json=json_data)
            self._add_log(_use_logging, _logger, 'Ger request ' + f'{url}' + ' Request code: ' + f'{request_result.status_code}')

            if request_result.status_code == 200:
                answer = request_result.json()
                res = answer.get('result')
                if res=='ok':
                    datas = answer.get('data')

                    if len(datas)==0:
                        self._add_log(_use_logging, _logger, 'End import manufacturer. No more manufacturer.')
                        return False

                    languages = self.env['res.lang'].search(domain=[('active','=', True)]).mapped('code')    

                    count = 0
                    for data in datas:
                        count+=1

                        manufacturer_id = False
                        is_new_manufacturer = False

                        manufact_id = data['id']
                        manufact_name = self._correcting_name(data['name'])

                        mp_manufacturer_id = self.env['td.marketplace.manufacturer'].search(domain=[('marketplace_id','=',self.id), ('marketplace_code','=',manufact_id)])
                        if mp_manufacturer_id:
                            manufacturer_id = mp_manufacturer_id.manufacturer_id.with_context(no_update_offer_state=True)

                        if not manufacturer_id:
                            if manufact_name:
                                manufacturer_id = self.env['td.manufacturer'].with_context(no_update_offer_state=True).search(domain=[('name','=',manufact_name)], limit=1)

                        if not manufacturer_id:
                            if manufact_name:
                                manufacturer_id = self.env['td.manufacturer'].with_context(no_update_offer_state=True).create({
                                        'name': manufact_name,
                                    })
                            else:
                                manufacturer_id = self.env['td.manufacturer'].with_context(no_update_offer_state=True).create({
                                        'name': 'opencart_manufacturer',
                                    })

                            is_new_manufacturer = True  
                            self._add_log(_use_logging, _logger, f'{count}' + '. Create manufacturer: ' + f'{manufact_name}')

                        if is_new_manufacturer or ( not is_new_manufacturer and do_update ):  
                            if not is_new_manufacturer:
                                self._add_log(_use_logging, _logger, f'{count}' + '. Update manufacturer: ' + f'{manufacturer_id.id}')
                                manufacturer_id.ensure_one()

                            mp_manufacturer_field_id = self.env['td.marketplace.manufacturer.field'].with_context(no_update_offer_state=True).search(domain=[('marketplace_id','=',self.id),('manufacturer_id','=',manufacturer_id.id)])    
                            if not mp_manufacturer_field_id:
                                mp_manufacturer_field_id = self.env['td.marketplace.manufacturer.field'].with_context(no_update_offer_state=True).create({'marketplace_id':self.id, 'manufacturer_id':manufacturer_id.id})

                            manufact_descr = data['description']

                            default_description = next((item for item in manufact_descr if item['lang_locale'] == self.language_id.code), None)
                            if default_description:
                                t_descr_def = self._correcting_name(default_description['description'])
                                manufacturer_id.write({
                                        'description': t_descr_def,
                                    })
                            else:        
                                t_descr_def = ''

                            for languge in languages:
                                t_description = next((item for item in manufact_descr if item['lang_locale'] == languge), None)
                                if t_description:
                                    t_descr = self._correcting_name(t_description['description'])
                                    if not t_descr:
                                        t_descr = t_descr_def
                                    t_meta_title = t_description['meta_title']
                                    t_meta_description = t_description['meta_description']
                                    t_meta_keyword = t_description['meta_keyword']
                                else:        
                                    t_descr = t_descr_def
                                    t_meta_title = ''
                                    t_meta_description = ''
                                    t_meta_keyword = ''

                                manufacturer_id.with_context(lang=languge).description = t_descr
                                mp_manufacturer_field_id.with_context(no_update_offer_state=True, lang=languge).write({
                                        'oc_meta_title': t_meta_title,
                                        'oc_meta_description': t_meta_description,
                                        'oc_meta_keywords': t_meta_keyword,
                                    })    

                            self._opencart_import_manufacturer_extend(manufacturer_id, data)

                            if 'image' in data:    
                                base64_image = data['image'].split(',')[1]  
                                manufacturer_id.image_1920 = base64_image

                            oc_manuf_seo = data['seo']        
                            for seo in oc_manuf_seo:
                                mp_manufacturer_field_id.with_context(lang=seo['lang_locale']).write({
                                        'oc_seo_url': seo['keyword'],  
                                    })    

                        mp_manufacturer_id = self.env['td.marketplace.manufacturer'].search(domain=[('marketplace_id','=',self.id), ('manufacturer_id','=',manufacturer_id.id)])
                        if not mp_manufacturer_id:
                            mp_manufacturer_id = self.env['td.marketplace.manufacturer'].create({
                                    'manufacturer_id': manufacturer_id.id,
                                    'marketplace_id': self.id,
                                    'state': 'processed',
                                    'marketplace_code': data['id'],
                                }) 
                        else:
                            mp_manufacturer_id.write({'state': 'processed'})

                    self.env.cr.commit()
                    self._add_log(_use_logging, _logger, 'End import manufacturer.')
                    return True

                else:
                    self._add_log(_use_logging, _logger, 'End import manufacturer. No more manufacturer.')
                    return False

    def _opencart_import_manufacturer_extend(self, manufacturer_id, data):
        return True

    def opencart_load_order(self, order_id):
        if not self.use_api:
            raise UserError(_('Exchange works only using API'))

        if not self.api_url:
            raise UserError(_('API url not defined'))

        _use_logging = (self.env['ir.config_parameter'].sudo().get_param('td_marketplace.mc_use_logging') == 'True')
        self._add_log(_use_logging, _logger, f'Import order {order_id}')

        sale_order_id = False

        opencart_rest = Opencart(env=self.env)

        oc_session_id = self._get_token()
        if oc_session_id:

            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)        

            url = self.api_url + '/index.php?route=api/odooConnector/getOrder'
            url = url + '&api_token=' + oc_session_id

            json_data={'order_id': order_id}
            headers = {
                        'Content-Type': 'application/json',
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) CustomClient/1.0',
                    }    

            request_result = opencart_rest.request(marketplace_id=self.id, url=url, method='post', calledMethod='odooConnector/getOrder', headers=headers, data=json_data)
            res = request_result.get('result')
            if res=='ok':     
                data = request_result.get('data')

                sale_order_id = self.env['sale.order'].search(domain=[('td_marketplace_id','=',self.id), ('td_marketplace_code','=', data.get('id'))])
                if sale_order_id:
                    return sale_order_id

                if not self.opencart_check_order_status(data.get('order_status_id')):
                    return False

                customer_id = data.get('customer_id')
                partner_id = False
                if customer_id:
                    mc_partner_id = self.env['td.marketplace.partner'].search(domain=[('marketplace_id','=',self.id), ('marketplace_code','=', customer_id)])
                    if mc_partner_id:
                        partner_id = mc_partner_id.partner_id 

                    if not partner_id:

                        url =  self.api_url + '/index.php?route=api/odooConnector/getCustomers'
                        url = url + '&api_token=' + oc_session_id

                        json_data={'id': customer_id}
                        headers = {
                                    'Content-Type': 'application/json',
                                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) CustomClient/1.0',
                                } 

                        request_result = requests.post(url=url, headers=headers, json=json_data)
                        if request_result.status_code == 200:
                            answer = request_result.json()
                            res = answer.get('result')
                            if res=='ok':
                                datas = answer.get('data')
                                if len(datas):
                                    partner_id = self._oc_update_partner(datas[0], True)
                else:
                    oc_customer = data.get('customer')   
                    oc_billing = data.get('billing')   

                    name = oc_customer['first_name'] + ' ' + oc_customer['last_name']
                    email = oc_customer['email']
                    phone = oc_customer['phone']

                    partner_id = False          
                    if name.strip() and email.strip() and phone.strip():                       
                        partner_id = self.env['res.partner'].search(domain=[('name','=',name), ('email','=',email), ('phone','=',phone)], limit=1)

                    if not partner_id and name.strip() and phone.strip():    
                        partner_id = self.env['res.partner'].search(domain=[('name','=',name), ('phone','=',phone)], limit=1)

                    if not partner_id and name.strip() and email.strip():    
                        partner_id = self.env['res.partner'].search(domain=[('name','=',name), ('email','=',email)], limit=1)

                    if not partner_id and name.strip() and email.strip():    
                        partner_id = self.env['res.partner'].search(domain=[('name','=',name)], limit=1)

                    if not partner_id and phone.strip():    
                        partner_id = self.env['res.partner'].search(domain=[('phone','=',phone)], limit=1)

                    if not partner_id and email.strip():    
                        partner_id = self.env['res.partner'].search(domain=[('email','=',email)], limit=1)


                    if not partner_id:
                        country_id = False
                        state_id = False

                        if oc_billing.get('country'):
                            country_id = self.env['res.country'].search(domain=[('code','=',oc_billing.get('country'))])

                        if country_id and oc_billing.get('state'):
                            state_id = self.env['res.country.state'].search(domain=[('country_id','=',country_id.id), ('code','=',oc_billing.get('state'))])    

                        city = oc_billing.get('city')
                        street = oc_billing.get('address_1')

                        c_name = name if name.strip() else email if email.strip() else phone
                        partner_id = self.env['res.partner'].create({
                                                                    'name': c_name,
                                                                    'email': email,
                                                                    'phone': phone,
                                                                    'country_id': country_id.id if country_id else False,
                                                                    'state_id': state_id.id if state_id else False,
                                                                    'city': city if city else '',
                                                                    'street': street if street else '',
                                                                })
                    
                if not partner_id:
                    self._add_log(_use_logging, _logger, _('Partner not found'))
                    raise UserError(_('Partner not found'))                

                oc_shipping = data.get('shipping')
                sh_name = oc_shipping['first_name'] + ' ' + oc_shipping['last_name']
                sh_city = oc_shipping.get('city')
                sh_street = oc_shipping.get('address_1')

                if (partner_id.name != sh_name) or (partner_id.city != sh_city) or (partner_id.street != sh_street):
                    partner_shipping_id = self.env['res.partner'].search(domain=[
                                                                                    ('parent_id','=',partner_id.id),
                                                                                    ('type','=','delivery'),
                                                                                    ('name','=',sh_name),
                                                                                    ('city','=',sh_city),
                                                                                    ('street','=',sh_street),
                                                                                ], limit=1)
                    if not partner_shipping_id:
                        partner_shipping_id = self.env['res.partner'].create({
                                                                                'parent_id': partner_id.id,
                                                                                'type': 'delivery',
                                                                                'name': sh_name,
                                                                                'city': sh_city,
                                                                                'street': sh_street,
                                                                            })
                else:
                    partner_shipping_id = partner_id

                oc_customer_group = int(data.get('customer_group_id', 0))
                price_list_id = self.env['td.marketplace.pricelist'].search(domain=[('marketplace_id','=',self.id),('marketplace_code','=',oc_customer_group)], limit=1).pricelist_id

                order_line_vals = []

                is_order_warning = False
                lines = data.get('line_items',[])
                for line in lines:
                    mp_product_id = line['product_id']
                    mp_variant_id = line['variant_id']

                    if mp_variant_id:
                        offer_id = self.env['td.offer'].search(domain=[('marketplace_id','=',self.id), ('marketplace_variant_code','=', mp_variant_id)])
                    else:
                        offer_id = self.env['td.offer'].search(domain=[('marketplace_id','=',self.id), ('marketplace_code','=', mp_product_id)])

                    if not offer_id:
                        error_text = f'Product not found: product_id {mp_product_id} / variant_id {mp_variant_id}'
                        # self._add_log(_use_logging, _logger, _('Product not found'))
                        # raise UserError(_('Product not found'))    
                        self._add_log(_use_logging, _logger, _(error_text))
                        raise UserError(_(error_text))    

                    is_warning = False
                    if len(offer_id) > 1:
                        is_warning = True
                        is_order_warning = True
                        offer_id = offer_id[0]

                    product_id = offer_id.product_id
                    product_tmpl_id = product_id.product_tmpl_id

                    order_line_vals.append(
                        (0, 0, {'name': product_tmpl_id.name,
                            'product_template_id': product_tmpl_id.id,
                            'product_id': product_id.id,
                            'product_uom_qty': line['quantity'],
                            'price_unit': line['price'],
                            'td_marketplace_warning': is_warning,
                            })                        
                    )

                sale_order_id = self.env['sale.order'].create({
                                                                'partner_id': partner_id.id,  
                                                                'partner_shipping_id': partner_shipping_id.id,
                                                                'td_marketplace_id': self.id,
                                                                'td_marketplace_number': data.get('number'),   
                                                                'td_marketplace_code': data.get('id'),   
                                                                'note': data.get('comment'),
                                                                'date_order': data.get('date_created'),
                                                                'pricelist_id': price_list_id.id,
                                                                'td_marketplace_warning': is_order_warning,
                                                                'order_line': order_line_vals,
                                                            })

                sale_order_id.order_line._compute_name()                             

        return sale_order_id                                                

    def opencart_check_order_status(self, order_status_id): 
        return True
        
    def _oc_get_product_by_variant(self, product_tmpl_id, oc_option_id, oc_variant, q_filter_option_name_tmpl):

        product_id = False
        option_ids = []
        q_filter_option_name = q_filter_option_name_tmpl.replace('%value%', oc_variant['value'][0]['name'])        
        query = """
                SELECT
                    ptav.id
                FROM td_marketplace_attribute mpa
                INNER JOIN product_attribute_value pav
                ON mpa.attribute_id = pav.attribute_id
                INNER JOIN product_template_attribute_value ptav
                ON ptav.product_tmpl_id = %s
                AND ptav.product_attribute_value_id=pav.id
                AND (""" + q_filter_option_name + """)
                WHERE mpa.marketplace_id = %s and mpa.marketplace_code=%s and mpa.prefix='opt'
                ORDER BY ptav.id asc                              
                """ 
        params = [product_tmpl_id.id, self.id, str(oc_option_id)]   
        self.env.cr.execute(query, params)
        res = self.env.cr.dictfetchall()
        for row in res:
            option_ids.append(str(row['id']))

        option_ids.sort(key=int)                                    
        combination_indices = ','.join(option_ids)        

        product_ids = product_tmpl_id.product_variant_ids.filtered(lambda x: x.combination_indices==combination_indices)
        if product_ids:
            product_id = product_ids[0]  
            
        return product_id             

    def opencart_do_update(self):

        if not self.use_api:
            raise UserError(_('Exchange works only using API'))

        if not self.api_url:
            raise UserError(_('API url not defined'))

        opencart_rest = Opencart()

        oc_session_id = self._get_token()
        if oc_session_id:

            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)    

            manufacturers_ids = self.env['td.marketplace.manufacturer'].search(domain=[('marketplace_id','=',self.id), ('state','=','to_process')], limit=100)
            has_update = (len(manufacturers_ids) > 0)
            for mp_manufacturer in manufacturers_ids:
                manufacturer = mp_manufacturer.manufacturer_id
                manufacturer_data = {}
                is_new = not mp_manufacturer.marketplace_code
                manufacturer_data = self._oc_get_manufacturer_data(manufacturer)
                if is_new:
                    json_data = manufacturer_data
                    headers = {
                                'Content-Type': 'application/json',
                                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) CustomClient/1.0',
                            }  

                    url =  self.api_url + '/index.php?route=api/odooConnector/addManufacturer'
                    url = url + '&api_token=' + oc_session_id    

                    request_result = opencart_rest.request(marketplace_id=self.id, url=url, method='post', calledMethod='odooConnector/addManufacturer', headers=headers, data=json_data)
                    res = request_result.get('result')
                    if res=='ok':     
                        mp_manufacturer.marketplace_code = request_result.get('id')
                        mp_manufacturer.state = 'processed'
                    else:    
                        raise UserError(_('The site returned an error when exchanging'))

                else:
                    
                    manufacturer_data.update({'id': mp_manufacturer.marketplace_code})

                    json_data = manufacturer_data
                    headers = {
                                'Content-Type': 'application/json',  
                                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) CustomClient/1.0',
                            }            

                    url =  self.api_url + '/index.php?route=api/odooConnector/updateManufacturer'
                    url = url + '&api_token=' + oc_session_id    

                    request_result = opencart_rest.request(marketplace_id=self.id, url=url, method='post', calledMethod='odooConnector/updateManufacturer', headers=headers, data=json_data)
                    res = request_result.get('result')
                    if res=='ok':     
                        mp_manufacturer.state = 'processed'
                    else:    
                        raise UserError(_('The site returned an error when exchanging'))
                self.env.cr.commit()

            offer_ids = self.env['td.offer'].search(domain=[('marketplace_id','=',self.id), ('state','in',('to_process', 'to_process_all'))], limit=100)
            has_update = (len(offer_ids) > 0)
            for offer in offer_ids:

                product_tmpl = offer.product_id.product_tmpl_id
                product_data = {}

                if product_tmpl.product_variant_count == 1:
                    # no variants
                    is_new = not offer.marketplace_code
                    product_data = self._oc_get_product_data(product_tmpl)

                    if is_new:
                        json_data = product_data
                        headers = {
                                    'Content-Type': 'application/json',
                                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) CustomClient/1.0',
                                }  

                        url =  self.api_url + '/index.php?route=api/odooConnector/addProduct'
                        url = url + '&api_token=' + oc_session_id    

                        request_result = opencart_rest.request(marketplace_id=self.id, url=url, method='post', calledMethod='odooConnector/addProduct', headers=headers, data=json_data)
                        res = request_result.get('result')
                        if res=='ok':     
                            offer.marketplace_code = request_result.get('id')
                            offer.state = 'processed'
                        else:    
                            raise UserError(_('The site returned an error when exchanging'))
                    else:
                        
                        product_data.update({'id': offer.marketplace_code})

                        json_data = product_data
                        headers = {
                                    'Content-Type': 'application/json',  
                                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) CustomClient/1.0',
                                }            

                        url =  self.api_url + '/index.php?route=api/odooConnector/updateProduct'
                        url = url + '&api_token=' + oc_session_id    

                        request_result = opencart_rest.request(marketplace_id=self.id, url=url, method='post', calledMethod='odooConnector/updateProduct', headers=headers, data=json_data)
                        res = request_result.get('result')
                        if res=='ok':     
                            offer.state = 'processed'
                        else:    
                            raise UserError(_('The site returned an error when exchanging'))
                else:    
                    is_new = not offer.marketplace_code
                    if is_new:
                        # check, that is a new product or is a new variant
                        product_variant_ids = product_tmpl.product_variant_ids.mapped('id')
                        prod_offers_ids = self.env['td.offer'].search(domain=[('marketplace_id','=',self.id), ('product_id','in',product_variant_ids)]).filtered(lambda x: x.marketplace_code)
                        if prod_offers_ids:
                            is_new = False
                            offer.marketplace_code = prod_offers_ids[0].marketplace_code

                    if is_new:
                        product_data = self._oc_get_product_data(product_tmpl)
                        json_data = product_data
                        headers = {
                                    'Content-Type': 'application/json',  
                                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) CustomClient/1.0',
                                }            

                        url =  self.api_url + '/index.php?route=api/odooConnector/addProduct'
                        url = url + '&api_token=' + oc_session_id    

                        request_result = opencart_rest.request(marketplace_id=self.id, url=url, method='post', calledMethod='odooConnector/addProduct', headers=headers, data=json_data)
                        res = request_result.get('result')
                        if res=='ok':     
                            offer.marketplace_code = request_result.get('id')
                            # offer.state = 'processed'
                        else:    
                            raise UserError(_('The site returned an error when exchanging'))

                        product_variant_data = self._oc_get_product_variant_data(offer.product_id)
                        product_variant_data.update({'product_id': offer.marketplace_code})
                        headers = {
                                    'Content-Type': 'application/json', 
                                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) CustomClient/1.0',
                                }            

                        url =  self.api_url + '/index.php?route=api/odooConnector/addProductVariant'
                        url = url + '&api_token=' + oc_session_id    

                        request_result = opencart_rest.request(marketplace_id=self.id, url=url, method='post', calledMethod='odooConnector/addProduct', headers=headers, data=product_variant_data)
                        res = request_result.get('result')
                        if res=='ok':     
                            offer.marketplace_variant_code = request_result.get('id')
                            offer.state = 'processed'
                        else:    
                            raise UserError(_('The site returned an error when exchanging'))
                    else:

                        product_data = self._oc_get_product_data(product_tmpl)
                        product_data.update({'id': offer.marketplace_code})

                        json_data = product_data
                        headers = {
                                    'Content-Type': 'application/json',  
                                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) CustomClient/1.0',
                                }  

                        url =  self.api_url + '/index.php?route=api/odooConnector/updateProduct'
                        url = url + '&api_token=' + oc_session_id    

                        request_result = opencart_rest.request(marketplace_id=self.id, url=url, method='post', calledMethod='odooConnector/updateProduct', headers=headers, data=json_data)
                        res = request_result.get('result')
                        if res=='ok':     
                            offer.state = 'processed'
                        else:    
                            raise UserError(_('The site returned an error when exchanging'))

                        if not offer.marketplace_variant_code:
                            product_variant_data = self._oc_get_product_variant_data(offer.product_id)
                            product_variant_data.update({'product_id': offer.marketplace_code})
                            headers = {
                                        'Content-Type': 'application/json',
                                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) CustomClient/1.0',            
                                    }  

                            url =  self.api_url + '/index.php?route=api/odooConnector/addProductVariant'
                            url = url + '&api_token=' + oc_session_id    

                            request_result = opencart_rest.request(marketplace_id=self.id, url=url, method='post', calledMethod='odooConnector/addProductVariant', headers=headers, data=product_variant_data)
                            res = request_result.get('result')
                            if res=='ok':     
                                offer.marketplace_variant_code = request_result.get('id')
                                offer.state = 'processed'
                            else:    
                                raise UserError(_('The site returned an error when exchanging'))
                        else:        
                            product_variant_data = self._oc_get_product_variant_data(offer.product_id)
                            product_variant_data.update({'product_id': offer.marketplace_code})
                            product_variant_data.update({'variant_id': offer.marketplace_variant_code})
                            headers = {
                                        'Content-Type': 'application/json',
                                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) CustomClient/1.0',            
                                    }  

                            url =  self.api_url + '/index.php?route=api/odooConnector/updateProductVariant'
                            url = url + '&api_token=' + oc_session_id    

                            request_result = opencart_rest.request(marketplace_id=self.id, url=url, method='post', calledMethod='odooConnector/updateProductVariant', headers=headers, data=product_variant_data)
                            res = request_result.get('result')
                            if res=='ok':     
                                offer.state = 'processed'
                            else:    
                                raise UserError(_('The site returned an error when exchanging'))

                self.env.cr.commit()
            return has_update

        else:   
            raise UserError(_('Invalid token'))
            return False        

    def _oc_get_manufacturer_data(self, manufacturer):
        manufacturer_data = {}
        manufacturer_data.update({'name': manufacturer.name})

        image_manuf = manufacturer.image_1920
        if image_manuf:
            manufacturer_data.update({'image': image_data_uri(image_manuf)})

        mp_manufacturer_field_id = self.env['td.marketplace.manufacturer.field'].search(domain = [('marketplace_id','=',self.id), ('manufacturer_id','=',manufacturer.id)])

        lang_data = []
        seo_data = []

        for language in self.language_ids:
            descr_data = {'id': language.marketplace_code}
            c_name = getattr(manufacturer.with_context(lang=language.language_code), 'description')
            descr_data.update({'description': c_name})

            if mp_manufacturer_field_id:
                c_name = getattr(mp_manufacturer_field_id.with_context(lang=language.language_code), 'oc_meta_title')
                descr_data.update({'meta_title': c_name})

                c_name = getattr(mp_manufacturer_field_id.with_context(lang=language.language_code), 'oc_meta_description')
                descr_data.update({'meta_description': c_name})

                c_name = getattr(mp_manufacturer_field_id.with_context(lang=language.language_code), 'oc_meta_keywords')
                descr_data.update({'meta_keyword': c_name})

                c_name = getattr(mp_manufacturer_field_id.with_context(lang=language.language_code), 'oc_seo_url')
                seo_data.append( {'id': language.marketplace_code, 'keyword': c_name} ) 
            else:    
                descr_data.update({'meta_title': ''})
                descr_data.update({'meta_description': ''})
                descr_data.update({'meta_keyword': ''})
                seo_data.append( {'id': language.marketplace_code, 'keyword': ''} ) 

            lang_data.append(descr_data)

        manufacturer_data.update({'description': lang_data})
        manufacturer_data.update({'seo': seo_data})

        return manufacturer_data

    def _oc_get_product_data(self, product_tmpl):
        product_data = {}

        product_data.update({'model':           product_tmpl.default_code})
        product_data.update({'manufacturer':    product_tmpl.td_manufacturer_id.name})
        mp_manufacturer = self.env['td.marketplace.manufacturer'].search(domain = [('marketplace_id','=',self.id), ('manufacturer_id','=',product_tmpl.td_manufacturer_id.id)])
        if mp_manufacturer:
            product_data.update({'manufacturer_id': mp_manufacturer.marketplace_code})

        regular_price_list_id = self.env['td.marketplace.pricelist'].search(domain=[('marketplace_id','=',self.id), ('pricelist_type','=','regular')]).pricelist_id
        if regular_price_list_id:
            price = self.get_product_price(product_tmpl, regular_price_list_id).get('price',0.0)
            if not float_is_zero(price, precision_digits=2):
                product_data.update({'price':    price})    

        product_data.update({'length':          product_tmpl.td_length})
        product_data.update({'width':           product_tmpl.td_width})
        product_data.update({'height':          product_tmpl.td_height})
        if self.language_id:
            product_data.update({'dimension_uom':   product_tmpl.with_context(lang=self.language_id.code).td_uom_dimension.name})
        else:    
            product_data.update({'dimension_uom':   product_tmpl.td_uom_dimension.name})

        product_data.update({'weight':          product_tmpl.td_weight})
        if self.language_id:
            product_data.update({'weight_uom':   product_tmpl.with_context(lang=self.language_id.code).td_uom_weight.name})
        else:    
            product_data.update({'weight_uom':   product_tmpl.td_uom_weight.name})
        # product_data.update({'quantity':        product_tmpl.qty_available})
        if product_tmpl.product_variant_count == 1:
            product_data.update({'quantity':        product_tmpl.product_variant_id.free_qty})

        category_ids = self.env['td.marketplace.category.product'].search(domain=[
                                                                                ('marketplace_id','=',self.id),
                                                                                ('product_tmpl_id','=',product_tmpl.id)
                                                                            ])
        if category_ids:
            product_data.update({'category_id': category_ids[0].category_id.code})
        else:
            product_data.update({'category_id': 0})

        mp_product_field_id = self.env['td.marketplace.product.field'].search(domain = [('marketplace_id','=',self.id), ('product_tmpl_id','=',product_tmpl.id)])
        if mp_product_field_id.oc_date_available:
            product_data.update({'date_available': str(mp_product_field_id.oc_date_available)})

        # description by languages
        lang_data = []
        seo_data = []
        for language in self.language_ids:
            descr_data = {'id': language.marketplace_code}

            c_name = getattr(product_tmpl.with_context(lang=language.language_code), 'name')
            descr_data.update({'name': c_name})

            c_name = getattr(product_tmpl.with_context(lang=language.language_code), 'description')
            descr_data.update({'description': c_name})

            if mp_product_field_id:
                c_name = getattr(mp_product_field_id.with_context(lang=language.language_code), 'oc_meta_title')
                descr_data.update({'meta_title': c_name})

                c_name = getattr(mp_product_field_id.with_context(lang=language.language_code), 'oc_meta_description')
                descr_data.update({'meta_description': c_name})

                c_name = getattr(mp_product_field_id.with_context(lang=language.language_code), 'oc_meta_keywords')
                descr_data.update({'meta_keyword': c_name})

                c_name = getattr(mp_product_field_id.with_context(lang=language.language_code), 'oc_tag')
                descr_data.update({'tag': c_name})

                c_name = getattr(mp_product_field_id.with_context(lang=language.language_code), 'oc_seo_url')
                seo_data.append( {'id': language.marketplace_code, 'keyword': c_name} ) 
            else:    
                descr_data.update({'meta_title': ''})
                descr_data.update({'meta_description': ''})
                descr_data.update({'meta_keyword': ''})
                descr_data.update({'tag': ''})
                seo_data.append( {'id': language.marketplace_code, 'keyword': ''} ) 

            lang_data.append(descr_data)

        product_data.update({'description': lang_data})
        product_data.update({'seo': seo_data})

        # main image
        image_prod = product_tmpl.image_1920
        if image_prod:
            product_data.update({'image': image_data_uri(image_prod)})

        # images
        images_data = []
        images_ids = self.env['product.image'].search(domain=[('product_tmpl_id','=',product_tmpl.id)])
        for image in images_ids:
            if image.image_1920:
                # image_name = image.name
                image_name = f'{image.name}_{image.id}'
                image_name = self.env['td.marketplace']._translite_text(image_name)
                image_name = self.env['td.marketplace']._sanitaze_text(image_name)        

                image_data = {'odoo_id': image.id}
                image_data.update({'name': image_name})
                image_data.update({'image': image_data_uri(image.image_1920)})
                image_data.update({'sort_order': image.sequence})
                images_data.append(image_data)

        product_data.update({'images': images_data})

        # attributes
        attributes_data = []
        query = """
                SELECT
                    tb.product_tmpl_id,
                    tb.id,
                    tb.attribute_id,
                    tb.name,
                    tb.attribute_value_id,
                    tb.value_name,
                    tb.td_make_variant,
                    ma.marketplace_code,
                    ma.prefix prefix
                FROM
                (
                    SELECT
                        ptav.product_tmpl_id,
                        ptav.id,
                        ptav.attribute_id attribute_id,
                        pa.name name,
                        ptav.product_attribute_value_id attribute_value_id,
                        pav.name value_name,
                        COALESCE(ptal.td_make_variant, False) td_make_variant
                    FROM
                    (
                        SELECT
                            ptav.id,
                            ptav.product_attribute_value_id,
                            ptav.product_tmpl_id,
                            ptav.attribute_id,
                            ptav.attribute_line_id
                        FROM product_template_attribute_value ptav
                        WHERE ptav.product_tmpl_id = %s
                    ) ptav    
                    LEFT JOIN product_template_attribute_line ptal
                    ON ptav.attribute_line_id = ptal.id
                    LEFT JOIN product_attribute pa
                    ON ptav.attribute_id = pa.id
                    LEFT JOIN product_attribute_value pav
                    ON ptav.product_attribute_value_id = pav.id
                ) tb
                LEFT JOIN td_marketplace_attribute ma
                ON ma.marketplace_id = %s
                AND ma.attribute_id = tb.attribute_id
                AND CASE WHEN tb.td_make_variant THEN ma.prefix='opt' ELSE ma.prefix='atr' END
                ORDER BY tb.attribute_id, tb.attribute_value_id                 
                """
        params = [product_tmpl.id, self.id]

        self.env.cr.execute(query, params)
        q_res = self.env.cr.dictfetchall()

        has_variants = False

        for q_row in q_res:
            if q_row['marketplace_code']:
                attribute = next( (item for item in attributes_data if item.get('odoo_id')==q_row['attribute_id']), None)
                if not attribute:
                    attribute_id = self.env['product.attribute'].browse(q_row['attribute_id'])
                    attribute = {
                                    'odoo_id': q_row['attribute_id'], 
                                    'id': int(q_row['marketplace_code']),
                                    'type': q_row['prefix'],	
                                    'variation': q_row['td_make_variant'],	
                                    'values':[],
                                }
                        
                    description = []
                    for language in self.language_ids:
                        descr_data = {'id': language.marketplace_code}
                        c_name = getattr(attribute_id.with_context(lang=language.language_code), 'name')
                        descr_data.update({'name': c_name})
                        description.append(descr_data)
                    attribute.update({'description': description})   

                    attributes_data.append(attribute)

                    has_variants = max(has_variants, q_row['td_make_variant'])

                attribute_value = next( (item for item in attribute['values'] if item==q_row['value_name']), None)
                if not attribute_value:
                    attribute_value_id = self.env['product.attribute.value'].browse(q_row['attribute_value_id'])
                    description = []
                    for language in self.language_ids:
                        descr_data = {'id': language.marketplace_code}
                        c_name = getattr(attribute_value_id.with_context(lang=language.language_code), 'name')
                        descr_data.update({'name': c_name})
                        description.append(descr_data)

                    attribute['values'].append(description)  

        product_data.update({'attributes': attributes_data})
        product_data.update({'type': 'simple' if not has_variants else 'variable'})

        # discounts:pricelist
        sale_price_lists = self.pricelist_ids.filtered(lambda x: x.pricelist_type=='sale' and x.marketplace_code)
        discounts = []
        for sale_price_list in sale_price_lists:
            discount_data = self.get_product_price(product_tmpl, sale_price_list.pricelist_id)
            if not float_is_zero(discount_data.get('price',0.0), precision_digits=2):
                discounts.append({
                                    'customer_group_id': sale_price_list.marketplace_code,
                                    'price': discount_data.get('price', 0.0),
                                    'quantity': discount_data.get('min_quantity', 0.0),
                                    'date_start': discount_data.get('date_start', '0000-00-00'),
                                    'date_end': discount_data.get('date_end', '0000-00-00'),
                                })
        product_data.update({'discount': discounts})

        # promotions:pricelist
        sale_price_lists = self.pricelist_ids.filtered(lambda x: x.pricelist_type=='promotion')
        discounts = []
        for sale_price_list in sale_price_lists:
            discount_data = self.get_product_price(product_tmpl, sale_price_list.pricelist_id)
            if not float_is_zero(discount_data.get('price',0.0), precision_digits=2):
                discounts.append({
                                    'price': discount_data.get('price', 0.0),
                                    'quantity': discount_data.get('min_quantity', 0.0),
                                    'date_start': discount_data.get('date_start', '0000-00-00'),
                                    'date_end': discount_data.get('date_end', '0000-00-00'),
                                })
        product_data.update({'promotion': discounts})

        return product_data

    def _oc_get_product_variant_data(self, product):
        product_variant_data = {}
        regular_price_list_id = self.env['td.marketplace.pricelist'].search(domain=[('marketplace_id','=',self.id), ('pricelist_type','=','regular')]).pricelist_id
        if regular_price_list_id:
            price = self.get_product_price(product.product_tmpl_id, regular_price_list_id).get('price',0.0)
            variant_price = self.get_product_variant_price(product, regular_price_list_id).get('price',0.0)
            if not float_is_zero(variant_price, precision_digits=2):
                if variant_price > price:
                    product_variant_data.update({
                                                    'price': variant_price - price,
                                                    'price_sign': '+'
                                                    })    
                else:                                    
                    product_variant_data.update({
                                                    'price': price - variant_price,
                                                    'price_sign': '-'
                                                    })    

        # product_variant_data.update({'quantity':    '{:.2f}'.format(product.qty_available)})   
        product_variant_data.update({'quantity':    '{:.2f}'.format(product.free_qty)})   

        product_weight = product.product_tmpl_id.td_weight       
        variant_weight = product.td_weight
        if not float_is_zero(variant_weight, precision_digits=2):
            if variant_weight == product_weight:
                product_variant_data.update({
                                                'weight': 0,
                                                'weight_sign': '+'
                                            })    
            elif variant_weight > product_weight:
                product_variant_data.update({
                                                'weight': variant_weight - product_weight,
                                                'weight_sign': '+'
                                            })    
            else:
                product_variant_data.update({
                                                'weight': product_weight - variant_weight,
                                                'weight_sign': '-'
                                            })    

        pav_ids = tuple([int(item) for item in product.combination_indices.split(',')])
        query = """
                SELECT
                    ptav.product_attribute_value_id attribute_value_id,
                    ptav.attribute_id,
                    ma.marketplace_code
                FROM (
                        SELECT
                            ptav.product_attribute_value_id,
                            ptav.attribute_id
                        FROM product_template_attribute_value ptav
                        WHERE ptav.id in %s
                ) ptav    
                INNER JOIN td_marketplace_attribute ma
                ON ma.marketplace_id = %s and ma.prefix='opt'
                AND ma.attribute_id = ptav.attribute_id        
                """
        params = [pav_ids, self.id]

        self.env.cr.execute(query, params)
        q_res = self.env.cr.dictfetchall()

        attributes = []
        for q_row in q_res:
            attribute_value_id = self.env['product.attribute.value'].browse(q_row['attribute_value_id'])
            attribute = {
                            'id': int(q_row['marketplace_code']),
                        }
            description = []
            for language in self.language_ids:
                descr_data = {'id': language.marketplace_code}
                c_name = getattr(attribute_value_id.with_context(lang=language.language_code), 'name')
                descr_data.update({'name': c_name})
                description.append(descr_data)
            attribute.update({'value': description})   

            attributes.append(attribute)

        product_variant_data.update({'attributes': attributes})   
        product_variant_data.update({'manage_stock': True}) 

        return product_variant_data

    def opencart_do_update_stock(self):

        if not self.use_api:
            raise UserError(_('Exchange works only using API'))

        if not self.api_url:
            raise UserError(_('API url not defined'))

        opencart_rest = Opencart(env=self.env)

        oc_session_id = self._get_token()
        if oc_session_id:

            offer_ids = self.env['td.offer'].search(domain=[('marketplace_id','=',self.id), ('state','in',('to_process_stock','to_process_all'))], limit=100)
            has_update = (len(offer_ids) > 0)
            for offer in offer_ids:
                product_id = offer.product_id

                product = {}

                if offer.marketplace_code and offer.marketplace_variant_code:
                    product.update({'quantity':    '{:.2f}'.format(product_id.free_qty)})    
                    regular_price_list_id = self.env['td.marketplace.pricelist'].search(domain=[('marketplace_id','=',self.id), ('pricelist_type','=','regular')]).pricelist_id
                    if regular_price_list_id:
                        price = self.get_product_price(product_id.product_tmpl_id, regular_price_list_id).get('price',0.0)
                        variant_price = self.get_product_variant_price(product_id, regular_price_list_id).get('price',0.0)
                        if not float_is_zero(variant_price, precision_digits=2):
                            if variant_price > price:
                                product.update({
                                                'price': variant_price - price,
                                                'price_sign': '+'
                                                })    
                            else:                                    
                                product.update({
                                                'price': price - variant_price,
                                                'price_sign': '-'
                                                })    

                    product.update({'product_id': offer.marketplace_code})
                    product.update({'variant_id': offer.marketplace_variant_code})

                    headers = {
                                'Content-Type': 'application/json',
                                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) CustomClient/1.0',
                            }  

                    url =  self.api_url + '/index.php?route=api/odooConnector/updateProductVariant'
                    url = url + '&api_token=' + oc_session_id    

                    request_result = opencart_rest.request(marketplace_id=self.id, url=url, method='post', calledMethod='odooConnector/updateProductVariant', headers=headers, data=product)
                    res = request_result.get('result')
                    if res=='ok':     
                        if offer.state == 'to_process_all':
                            offer.state = 'to_process'
                        else:
                            offer.state = 'processed'
                    else:    
                        raise UserError(_('The site returned an error when exchanging'))

                product = {}
                if not offer.marketplace_variant_code:
                    product.update({'quantity':    '{:.2f}'.format(product_id.free_qty)})    

                regular_price_list_id = self.env['td.marketplace.pricelist'].search(domain=[('marketplace_id','=',self.id), ('pricelist_type','=','regular')]).pricelist_id
                if regular_price_list_id:
                    price = self.get_product_price(product_id.product_tmpl_id, regular_price_list_id).get('price',0.0)
                    if not float_is_zero(price, precision_digits=2):
                        product.update({'price': price})    

                # discounts:pricelist
                sale_price_lists = self.pricelist_ids.filtered(lambda x: x.pricelist_type=='sale' and x.marketplace_code)
                discounts = []
                for sale_price_list in sale_price_lists:
                    discount_data = self.get_product_price(product_id.product_tmpl_id, sale_price_list.pricelist_id)
                    if not float_is_zero(discount_data.get('price',0.0), precision_digits=2):
                        discounts.append({
                                            'customer_group_id': sale_price_list.marketplace_code,
                                            'price': discount_data.get('price', 0.0),
                                            'quantity': discount_data.get('min_quantity', 0.0),
                                            'date_start': discount_data.get('date_start', '0000-00-00'),
                                            'date_end': discount_data.get('date_end', '0000-00-00'),
                                        })
                product.update({'discount': discounts})

                # promotion:pricelist
                sale_price_lists = self.pricelist_ids.filtered(lambda x: x.pricelist_type=='promotion')
                discounts = []
                for sale_price_list in sale_price_lists:
                    discount_data = self.get_product_price(product_id.product_tmpl_id, sale_price_list.pricelist_id)
                    if not float_is_zero(discount_data.get('price',0.0), precision_digits=2):
                        discounts.append({
                                            # 'customer_group_id': sale_price_list.marketplace_code,
                                            'price': discount_data.get('price', 0.0),
                                            'quantity': discount_data.get('min_quantity', 0.0),
                                            'date_start': discount_data.get('date_start', '0000-00-00'),
                                            'date_end': discount_data.get('date_end', '0000-00-00'),
                                        })
                product.update({'promotion': discounts})

                product.update({'id': offer.marketplace_code})

                headers = {
                            'Content-Type': 'application/json',
                            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) CustomClient/1.0',
                        }  

                url =  self.api_url + '/index.php?route=api/odooConnector/updateProduct'
                url = url + '&api_token=' + oc_session_id    

                request_result = opencart_rest.request(marketplace_id=self.id, url=url, method='post', calledMethod='odooConnector/updateProduct', headers=headers, data=product)
                res = request_result.get('result')
                if res=='ok':     
                    if offer.state == 'to_process_all':
                        offer.state = 'to_process'
                    else:
                        offer.state = 'processed'
                else:    
                    raise UserError(_('The site returned an error when exchanging'))

                self.env.cr.commit()

            return has_update
        else:   
            raise UserError(_('Invalid token'))
            return False        

    def opencart_upload_pricelist(self, marketplace_pricelist_id):
        if not self.use_api:
            raise UserError(_('Exchange works only using API'))

        if not self.api_url:
            raise UserError(_('API url not defined'))

        oc_session_id = self._get_token()
        if oc_session_id:
            pricelist = marketplace_pricelist_id.pricelist_id
            description = []
            for language in self.language_ids:
                descr_data = {'id': language.marketplace_code}

                c_name = getattr(pricelist.with_context(lang=language.language_code), 'name')
                descr_data.update({'name': c_name})
                descr_data.update({'description': c_name})

                description.append(descr_data)

            json_data = description
            headers = {
                        'Content-Type': 'application/json',
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) CustomClient/1.0',
                    }  

            url =  self.api_url + '/index.php?route=api/odooConnector/addCustomerGroup'
            url = url + '&api_token=' + oc_session_id    

            request_result = requests.post(url=url, headers=headers, json=json_data)
            if request_result.status_code == 200:
                answer = request_result.json()
                res = answer.get('result')
                if res=='ok':     
                    marketplace_pricelist_id.marketplace_code = answer.get('id')
                else:    
                    raise UserError(_('The site returned an error when exchanging'))
            else: 
                raise UserError(_('The site returned an error when exchanging'))

    def opencart_upload_attribute(self, marketplace_attribute_id):
        if not self.use_api:
            raise UserError(_('Exchange works only using API'))

        if not self.api_url:
            raise UserError(_('API url not defined'))

        oc_session_id = self._get_token()
        if oc_session_id:
            attribute = marketplace_attribute_id.attribute_id
            description = []
            for language in self.language_ids:
                descr_data = {'id': language.marketplace_code}

                c_name = getattr(attribute.with_context(lang=language.language_code), 'name')
                descr_data.update({'name': c_name})
                description.append(descr_data)

            json_data = description
            headers = {
                        'Content-Type': 'application/json',
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) CustomClient/1.0',
                    }  

            if marketplace_attribute_id.prefix == 'opt':
                url =  self.api_url + '/index.php?route=api/odooConnector/addOption'
            else:
                url =  self.api_url + '/index.php?route=api/odooConnector/addAttribute'

            url = url + '&api_token=' + oc_session_id    

            request_result = requests.post(url=url, headers=headers, json=json_data)
            if request_result.status_code == 200:
                answer = request_result.json()
                res = answer.get('result')
                if res=='ok':     
                    marketplace_attribute_id.marketplace_code = answer.get('id')
                else:    
                    raise UserError(_('The site returned an error when exchanging'))
            else: 
                raise UserError(_('The site returned an error when exchanging'))

    def _get_token(self):
        # _use_logging = (self.env['ir.config_parameter'].sudo().get_param('td_marketplace.mc_use_logging') == 'True')
        # self._add_log(_use_logging, _logger, "Get token for: %s" % self.name)

        token = self.api_token
        token_expires = self.api_token_expires
        
        if token and token_expires and datetime.now(timezone.utc) < (token_expires - timedelta(days=1)).replace(tzinfo=timezone.utc):
            # self._add_log(_use_logging, _logger, "Token: %s" % token)
            return token
        else:
            # self._add_log(_use_logging, _logger, "Get token from marketplace")
            # opencart_rest = Opencart()
            # get token by login/pass
            url =  self.api_url + '/index.php?route=api/login'
            json_data={
                    'username': self.api_login,
                    'key': self.api_password,
                }        

            oc_session_id = False
            oc_session_expires = False
            oc_token = False

            headers = {
                'Content-Type': 'application/x-www-form-urlencoded',
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) CustomClient/1.0',
            }            

            request_result = requests.post(url, data=json_data, headers=headers)
            if request_result.status_code == 200:
                answer = request_result.json()
                # self._add_log(_use_logging, _logger, f"Answer: {answer}, text: {request_result.text}")
                oc_token = answer.get('token', answer.get('api_token'))
                if 'Set-Cookie' in request_result.headers:
                    set_cookie=request_result.headers['Set-Cookie']

                    pattern = r"expires=([^;]+)"
                    match = re.search(pattern, set_cookie)   
                    if match:
                        oc_session_expires = match.group(1)  

                        time_tuple = email.utils.parsedate_tz(oc_session_expires)
                        if time_tuple:
                            oc_session_expires = datetime(*time_tuple[:6])
                        else:    
                            self._add_log(_use_logging, _logger, f"Failed to parse date from Set-Cookie header: {oc_session_expires}")
                            oc_session_expires = datetime.now() + timedelta(days=60)

                if not oc_session_expires:
                    # NOTE +2 month from now
                    oc_session_expires = datetime.now() + timedelta(days=60)
            # else:
            #     self._add_log(_use_logging, _logger, f"Error request: {request_result.status_code}: {request_result.text}")        

            if oc_token and oc_session_expires:
                self.api_token = oc_token
                self.api_token_expires = oc_session_expires 
                return oc_token

        return False               

    def opencart_actualize_orders(self, sync_data):

        if not sync_data.get('sync_by', False):
            return    

        opencart_rest = Opencart(env=self.env)

        oc_session_id = self._get_token()
        if oc_session_id:
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)        

            url = self.api_url + '/index.php?route=api/odooConnector/getOrders'
            url = url + '&api_token=' + oc_session_id

            if sync_data['sync_by'] == 'date':
                date_from = sync_data['sync']
                json_data={
                    'date_after': f'{date_from.strftime("%Y-%m-%dT%H:%M:%S")}',
                    'page': 1,
                    'per_page': 100,
                    }
            elif sync_data['sync_by'] == 'id':
                last_id = sync_data['sync']        
                json_data={
                    'last_id': f'{last_id}',
                    'page': 1,
                    'per_page': 100,
                    }
            else:
                return        

            headers = {
                        'Content-Type': 'application/json',
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) CustomClient/1.0',
                    } 

            request_result = opencart_rest.request(marketplace_id=self.id, url=url, method='post', calledMethod='odooConnector/getOrders', headers=headers, data=json_data)
            res = request_result.get('result')
            if res=='ok':     
                orders = request_result.get('data')
                for order in orders:
                    self.opencart_load_order(order['id'])


