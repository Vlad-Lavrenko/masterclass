from odoo import fields, models
from datetime import datetime, timedelta
import re

class Marketplace(models.Model):
    _name = 'td.marketplace'
    _description = 'Marketplace'

    name = fields.Char( 
            required=True,
        )

    code = fields.Selection(
            selection=[],
            required=True,
        )

    image_128 = fields.Image(
            string='Image', 
            max_width=128, 
            max_height=128, 
        )

    template_id = fields.Many2one(
            comodel_name='ir.ui.view', 
            readonly=True, 
            ondelete='restrict', 
        )

    category_ids = fields.One2many(
            comodel_name='td.marketplace.category', 
            inverse_name='marketplace_id', 
        )

    category_count = fields.Integer(
            compute='_compute_category_count', 
        )

    attribute_ids = fields.One2many(
            comodel_name='td.marketplace.attribute', 
            inverse_name='marketplace_id', 
        )

    attribute_count = fields.Integer(
            compute='_compute_attribute_count', 
        )        

    manufacturer_ids = fields.One2many(
            comodel_name='td.marketplace.manufacturer', 
            inverse_name='marketplace_id', 
        )

    manufacturer_count = fields.Integer(
            compute='_compute_manufacturer_count', 
        )        

    to_process_manufacturer_count = fields.Integer(
            compute='_compute_to_process_manufacturer_count', 
        )


    partner_ids = fields.One2many(
            comodel_name='td.marketplace.partner', 
            inverse_name='marketplace_id', 
        )

    partner_count = fields.Integer(
            compute='_compute_partner_count', 
        )        

    language_ids = fields.One2many(
            comodel_name='td.marketplace.language', 
            inverse_name='marketplace_id', 
        )  

    offer_ids = fields.One2many(
            comodel_name='td.offer',
            inverse_name='marketplace_id',
        )     

    offer_count = fields.Integer(
            compute='_compute_offer_count', 
        )

    pricelist_ids = fields.One2many(
            comodel_name='td.marketplace.pricelist',
            inverse_name='marketplace_id',
        )     

    pricelist_count = fields.Integer(
            compute='_compute_pricelist_count', 
        )

    to_process_offer_count = fields.Integer(
            compute='_compute_to_process_offer_count', 
        )

    to_process_stock_offer_count = fields.Integer(
            compute='_compute_to_process_stock_offer_count', 
        )

    use_api = fields.Boolean() 
    api_url = fields.Char(
            string='URL'
        )     
    api_login = fields.Char(
            string='Login'
        )   
    api_password = fields.Char(
            string='Password'
        )   
    api_token = fields.Char(
            string='Token'
        )     
    api_token_expires = fields.Datetime(
            string='Token expires'
        )    

    odoo_url = fields.Char(
            string='odoo URL',
            default=lambda self: self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        )    

    marketplace_external_id = fields.Char(
            string = 'External ID',
        )         

    currency_id = fields.Many2one(
            comodel_name='res.currency',
            string="Currency",
        )

    weght_uom = fields.Many2one(
            comodel_name='uom.uom',
            string='Wegith Unit of Measure'
        )

    dimension_uom = fields.Many2one(
            comodel_name='uom.uom',
            string='Dimension Unit of Measure'
        )     

    language_id = fields.Many2one(
            comodel_name='res.lang',
            string="Language",
        )     

    auto_load_orders = fields.Boolean(
            string='Loading orders on schedule'
        )  

    order_sync = fields.Selection(
            selection=[('date', 'By date'), ('id', 'By id')],
            string='Order sync',
            default='date'
        )                       

    _sql_constraints = [
            ('marketplace_external_id_unique', 'UNIQUE(marketplace_external_id)', 'The marketplace external ID must be unique!'),
        ]        

    def load_marketplace_settings(self):
        self.ensure_one()
        if not hasattr(self, f'{self.code}_load_settings'):
            return False
        return getattr(self, f'{self.code}_load_settings')()

    def load_marketplace_category(self):
        self.ensure_one()
        if not hasattr(self, f'{self.code}_load_category'):
            return False
        return getattr(self, f'{self.code}_load_category')()

    def load_marketplace_product(self):
        self.ensure_one()            
        if not hasattr(self, f'{self.code}_load_product'):
            return False
        return getattr(self, f'{self.code}_load_product')()

    def load_marketplace_attribute(self):
        self.ensure_one()            
        if not hasattr(self, f'{self.code}_load_attribute'):
            return False
        return getattr(self, f'{self.code}_load_attribute')()

    def load_marketplace_language(self):
        self.ensure_one()            
        if not hasattr(self, f'{self.code}_load_language'):
            return False
        return getattr(self, f'{self.code}_load_language')()

    def load_marketplace_partner(self):
        self.ensure_one()            
        if not hasattr(self, f'{self.code}_load_partner'):
            return False
        return getattr(self, f'{self.code}_load_partner')()

    def load_marketplace_manufacturer(self):
        self.ensure_one()            
        if not hasattr(self, f'{self.code}_load_manufacturer'):
            return False
        return getattr(self, f'{self.code}_load_manufacturer')()

    def load_marketplace_pricelist(self):
        self.ensure_one()            
        if not hasattr(self, f'{self.code}_load_pricelist'):
            return False
        return getattr(self, f'{self.code}_load_pricelist')()

    def load_marketplace_order(self, order_id):
        self.ensure_one()            
        if not hasattr(self, f'{self.code}_load_order'):
            return False
        return getattr(self, f'{self.code}_load_order')(order_id)

    def _compute_category_count(self):
        for obj in self:
            obj.category_count = len(obj.category_ids)

    def _compute_attribute_count(self):
        for obj in self:
            obj.attribute_count = len(obj.attribute_ids)

    def _compute_partner_count(self):
        for obj in self:
            obj.partner_count = len(obj.partner_ids)

    def _compute_manufacturer_count(self):
        for obj in self:
            obj.manufacturer_count = len(obj.manufacturer_ids)

    def _compute_offer_count(self):
        for obj in self:
            obj.offer_count = len(obj.offer_ids)

    def _compute_pricelist_count(self):
        for obj in self:
            obj.pricelist_count = len(obj.pricelist_ids)

    def _compute_to_process_offer_count(self):
        for obj in self:
            count_offers = obj.offer_ids.filtered(
                lambda x: x.state in ('to_process','to_process_all'))
            obj.to_process_offer_count = len(count_offers)

    def _compute_to_process_stock_offer_count(self):
        for obj in self:
            count_offers = obj.offer_ids.filtered(
                lambda x: x.state in ('to_process_stock', 'to_process_all'))
            obj.to_process_stock_offer_count = len(count_offers)

    def _compute_to_process_manufacturer_count(self):
        for obj in self:
            count_manufacturers = obj.manufacturer_ids.filtered(
                lambda x: x.state == 'to_process')
            obj.to_process_manufacturer_count = len(count_manufacturers)

    def action_do_update(self):
        action = self.env.ref('td_marketplace.td_data_export_wizard_from_marketplace_act_window')    
        action['context'] = {
                                'default_marketplace_id': self.id,
                                'default_export_type': 'update',
                            }        
        
        return action.read()[0]    

    def _action_do_update(self):    
        self.ensure_one()            
        if not hasattr(self, f'{self.code}_do_update'):
            return False
        return getattr(self, f'{self.code}_do_update')()

    def action_do_update_stock(self):
        action = self.env.ref('td_marketplace.td_data_export_wizard_from_marketplace_act_window')    
        action['context'] = {
                                'default_marketplace_id': self.id,
                                'default_export_type': 'update_stock',
                            }        
        
        return action.read()[0]    

    def _action_do_update_stock(self):    
        self.ensure_one()            
        if not hasattr(self, f'{self.code}_do_update_stock'):
            return False
        return getattr(self, f'{self.code}_do_update_stock')()

    def upload_pricelist(self, marketplace_pricelist_id):
        self.ensure_one()            
        if not hasattr(self, f'{self.code}_upload_pricelist'):
            return False
        return getattr(self, f'{self.code}_upload_pricelist')(marketplace_pricelist_id)

    def upload_attribute(self, marketplace_attribute_id):
        self.ensure_one()            
        if not hasattr(self, f'{self.code}_upload_attribute'):
            return False
        return getattr(self, f'{self.code}_upload_attribute')(marketplace_attribute_id)

    def _add_log(self, add_log, logger, log):
        if add_log:
            logger.info(log)

    def action_download_orders(self):
        action = self.env.ref('td_marketplace.td_order_import_wizard_from_marketplace_act_window')    
        action['context'] = {
                                'default_marketplace_id': self.id,
                            }        
        
        return action.read()[0]    

    def get_product_price(self, product_tmpl_id, pricelist_id):
        result = {  
                    'price':0.0,
                    'min_quantity': 0.0,
                    'date_start': '0000-00-00',
                    'date_end': '0000-00-00',
                }
        if pricelist_id:
            price_list_item_id = self.env['product.pricelist.item'].search(domain=[
                                                                                    ('pricelist_id','=',pricelist_id.id),
                                                                                    ('product_tmpl_id','=', product_tmpl_id.id),
                                                                                    ('product_id','=', None),
                                                                                ])
            if price_list_item_id:
                result.update({'price':price_list_item_id.fixed_price})
                result.update({'min_quantity':price_list_item_id.min_quantity})
                if price_list_item_id.date_start:
                    result.update({'date_start': price_list_item_id.date_start.strftime('%Y-%m-%d')})
                if price_list_item_id.date_end:   
                    result.update({'date_end':price_list_item_id.date_end.strftime('%Y-%m-%d')})
        return result

    def get_product_variant_price(self, product_id, pricelist_id):
        result = {  
                    'price':0.0,
                    'min_quantity': 0.0,
                    'date_start': '0000-00-00',
                    'date_end': '0000-00-00',
                }

        if pricelist_id:
            price_list_item_id = self.env['product.pricelist.item'].search(domain=[
                                                                                    ('pricelist_id','=',pricelist_id.id),
                                                                                    ('product_tmpl_id','=', product_id.product_tmpl_id.id),
                                                                                    ('product_id','=', product_id.id),
                                                                                ])
            if price_list_item_id:
                result.update({'price':price_list_item_id.fixed_price})
                result.update({'min_quantity':price_list_item_id.min_quantity})
                if price_list_item_id.date_start:
                    result.update({'date_start': price_list_item_id.date_start.strftime('%Y-%m-%d')})
                if price_list_item_id.date_end:   
                    result.update({'date_end':price_list_item_id.date_end.strftime('%Y-%m-%d')})
        return result

    def action_cron_download_orders(self):
        # by marketplaces...
        marketplaces_ids = self.env['td.marketplace'].search(domain=[('use_api','=',True), ('auto_load_orders','=',True)])
        for marketplace in marketplaces_ids:
            marketplace._download_orders()
        return True

    def action_cron_update_stock(self):
        marketplaces_ids = self.env['td.marketplace'].search(domain=[('use_api','=',True), ('auto_load_orders','=',True)])
        for marketplace in marketplaces_ids:
            marketplace._action_do_update_stock()
        return True

    def _download_orders(self):    
        if not hasattr(self, f'{self.code}_actualize_orders'):
            return
        getattr(self, f'{self.code}_actualize_orders')(self._get_last_sync_data())

    def _get_last_sync_data(self):
        result = {'sync_by':False, 'sync':False}
        if self.order_sync == 'date':
            last_order_id = self.env['sale.order'].search(domain=[('td_marketplace_id','=',self.id)], order='date_order desc', limit=1)
            if last_order_id:
                last_date = last_order_id.date_order
            else:    
                last_date = (datetime.now() - timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
            result.update({'sync_by':self.order_sync, 'sync':last_date})    

        if self.order_sync == 'id':
            last_order_id = self.env['sale.order'].search(domain=[('td_marketplace_id','=',self.id)], order='td_marketplace_code desc', limit=1)   
            if last_order_id:
                last_id = last_order_id.td_marketplace_code
            else:    
                last_id = '0'
            result.update({'sync_by':self.order_sync, 'sync':last_id})    

        return result

# ---=== UTILS ===---
    def _correcting_name(self, name):
        t_name = name
        t_name = t_name.replace('&lt;', '<')
        t_name = t_name.replace('&gt;', '>')                                    
        t_name = t_name.replace('&#13;', '<br>')
        t_name = t_name.replace('&amp;', '&')
        t_name = t_name.replace('&quot;', '"')
        t_name = t_name.replace('&#039;', "'")
        t_name = t_name.replace('\n', '').replace('\t', '')
        

        # color`s clear
        t_name = re.sub(r'background-color: .{7};', '', t_name)
        t_name = re.sub(r'color: .{7};', '', t_name)

        return t_name

    def _sanitaze_text(self, text: str) -> str:

        result = text

        result = result.replace('(','')
        result = result.replace(')','')
        result = re.sub(r'[^a-zA-Z0-9]', '-', result)        
        while result.find('--')>0:
            result = result.replace('--','-')

        return result

    def _translite_text(self, text: str) -> str:

        result = text

        translit_dict = {
            'А': 'A', 'Б': 'B', 'В': 'V', 'Г': 'G', 'Д': 'D', 'Е': 'E', 'Ё': 'E', 'Ж': 'Zh', 
            'З': 'Z', 'И': 'I', 'Й': 'Y', 'К': 'K', 'Л': 'L', 'М': 'M', 'Н': 'N', 'О': 'O', 
            'П': 'P', 'Р': 'R', 'С': 'S', 'Т': 'T', 'У': 'U', 'Ф': 'F', 'Х': 'Kh', 'Ц': 'Ts', 
            'Ч': 'Ch', 'Ш': 'Sh', 'Щ': 'Shch', 'Ъ': '', 'Ы': 'Y', 'Ь': '', 'Э': 'E', 'Ю': 'Yu', 
            'Я': 'Ya', 'І': 'I',
            'Ґ': 'G','Є': 'Ye','Ї': 'Yi',
            'а': 'a', 'б': 'b', 'в': 'v', 'г': 'g', 'д': 'd', 'е': 'e', 'ё': 'e', 
            'ж': 'zh', 'з': 'z', 'и': 'i', 'й': 'y', 'к': 'k', 'л': 'l', 'м': 'm', 'н': 'n', 
            'о': 'o', 'п': 'p', 'р': 'r', 'с': 's', 'т': 't', 'у': 'u', 'ф': 'f', 'х': 'kh', 
            'ц': 'ts', 'ч': 'ch', 'ш': 'sh', 'щ': 'shch', 'ъ': '', 'ы': 'y', 'ь': '', 'э': 'e', 
            'ю': 'yu', 'я': 'ya',
            'ґ': 'g','є': 'ie', 'ї': 'yi', 'і': 'i'
        }        

        result = ''.join([translit_dict.get(char, char) for char in text])
        result = result.replace(" ", "-").lower()

        return result    