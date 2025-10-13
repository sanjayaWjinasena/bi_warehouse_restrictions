# -*- coding: utf-8 -*-
# Part of Browseinfo. See LICENSE file for full copyright and licensing details.


from odoo import api, fields, models,_
from odoo.osv import expression

from odoo.exceptions import ValidationError


class InheritStockPicking(models.Model):
    _inherit ="stock.picking"

    def search_fetch(self, domain, field_names, offset=0, limit=None, order=None):
        allowed_access = self.env.user.has_group('bi_warehouse_restrictions.group_restrict_operations')
        current_uid = self._context.get('uid')
        user = self.env['res.users'].browse(current_uid)
        domains =[]
        
        if user.restrict_operation and user.restrict_location and user.restrict_warehouse_list and allowed_access:
            domain += ['|','|',
            ('picking_type_id','in',self.env.user.operation_ids.ids),
            ('location_id','in',self.env.user.location_ids.ids),
            ('picking_type_id.warehouse_id','in',self.env.user.warehouse_ids.ids),]

        elif  user.restrict_operation and user.restrict_location and allowed_access :
            domain += ['|',('picking_type_id','in',self.env.user.operation_ids.ids),('location_id','in',self.env.user.location_ids.ids)]
        elif  user.restrict_operation and user.restrict_warehouse_list and allowed_access :
            domain += ['|',('picking_type_id','in',self.env.user.operation_ids.ids),('picking_type_id.warehouse_id','in',self.env.user.warehouse_ids.ids)]
    

        elif  user.restrict_location and user.restrict_warehouse_list and allowed_access :
            domain += ['|',('location_id','in',self.env.user.location_ids.ids),('picking_type_id.warehouse_id','in',self.env.user.warehouse_ids.ids)] 

        if user.restrict_operation and allowed_access:
            domain += [('picking_type_id','in',self.env.user.operation_ids.ids)]
        elif user.restrict_location and allowed_access:
            domain += [('location_id','in',self.env.user.location_ids.ids)]
        elif user.restrict_warehouse_list and allowed_access:
            domain += [('picking_type_id.warehouse_id','in',self.env.user.warehouse_ids.ids)]

        return super(InheritStockPicking, self).search_fetch(domain, field_names, offset, limit, order)

    @api.model
    def _name_search(self, name, domain=None, operator='ilike', limit=None, order=None):
        context = dict(self.env.context)
        allowed_access = self.env.user.has_group('bi_warehouse_restrictions.group_restrict_operations')
        current_uid = self._context.get('uid')
        user = self.env['res.users'].browse(current_uid)


        if user.restrict_operation and user.restrict_location and user.restrict_warehouse_list and allowed_access:
            domain += ['|','|',
            ('picking_type_id','in',self.env.user.operation_ids.ids),
            ('location_id','in',self.env.user.location_ids.ids),
            ('picking_type_id.warehouse_id','in',self.env.user.warehouse_ids.ids),]

        elif  user.restrict_operation and user.restrict_location and allowed_access :
            domain += ['|',('picking_type_id','in',self.env.user.operation_ids.ids),('location_id','in',self.env.user.location_ids.ids)]
        elif  user.restrict_operation and user.restrict_warehouse_list and allowed_access :
            domain += ['|',('picking_type_id','in',self.env.user.operation_ids.ids),('picking_type_id.warehouse_id','in',self.env.user.warehouse_ids.ids)]

        elif  user.restrict_location and user.restrict_warehouse_list and allowed_access :
            domain += ['|',('location_id','in',self.env.user.location_ids.ids),('picking_type_id.warehouse_id','in',self.env.user.warehouse_ids.ids)] 


        elif user.restrict_operation and allowed_access:
           domain += [('picking_type_id','in',self.env.user.operation_ids.ids)]
        elif user.restrict_location and allowed_access:
            domain += [('location_id','in',self.env.user.location_ids.ids)]
        elif user.restrict_warehouse_list and allowed_access:
            domain += [('picking_type_id.warehouse_id','in',self.env.user.warehouse_ids.ids)]

        return super(InheritStockPicking, self.sudo().with_context(context))._name_search(name, domain, operator, limit, order)

    @api.depends('picking_type_id', 'partner_id')
    def _compute_location_id(self):
        allowed_access = self.env.user.has_group('bi_warehouse_restrictions.group_restrict_operations')
        user = self.env.user
        final_location_ids = user.location_ids.ids

        for picking in self:
            if picking.state != 'draft' or picking.return_id:
                continue

            picking = picking.with_company(picking.company_id)
            if not picking.picking_type_id:
                continue

            # Determine locations (same logic as base)
            if picking.picking_type_id.default_location_src_id:
                location_id = picking.picking_type_id.default_location_src_id.id
            elif picking.partner_id:
                location_id = picking.partner_id.property_stock_supplier.id
            else:
                _customerloc, location_id = self.env['stock.warehouse']._get_partner_locations()

            if picking.picking_type_id.default_location_dest_id:
                location_dest_id = picking.picking_type_id.default_location_dest_id.id
            elif picking.partner_id:
                location_dest_id = picking.partner_id.property_stock_customer.id
            else:
                location_dest_id, _supplierloc = self.env['stock.warehouse']._get_partner_locations()

            # Apply restrictions
            if user.restrict_location and allowed_access:
                if location_id and location_id in final_location_ids:
                    picking.location_id = location_id
                else:
                    picking.location_id = False

                if location_dest_id and location_dest_id in final_location_ids:
                    picking.location_dest_id = location_dest_id
                else:
                    picking.location_dest_id = False
            else:
                # If restriction not active, set normal values
                picking.location_id = location_id
                picking.location_dest_id = location_dest_id

    def _check_user_location_restrictions(self):
        current_user = self.env.user
        for picking in self:
            if picking.location_id and current_user.allowed_destination_locations_ids and picking.location_id not in current_user.allowed_source_locations_ids:
                raise ValidationError(_(
                    "You are not allowed make picking for this '%s' source location "
                ) % picking.location_id.display_name)

            if picking.location_dest_id and current_user.allowed_destination_locations_ids and picking.location_dest_id not in current_user.allowed_destination_locations_ids:
                raise ValidationError(_(
                    "You are not allowed make picking for this '%s' Destination Location "
                ) % picking.location_dest_id.display_name)

    @api.model_create_multi
    def create(self, vals_list):
        pickings = super(InheritStockPicking, self).create(vals_list)
        pickings._check_user_location_restrictions()
        return pickings

    def write(self, vals):
        res = super(InheritStockPicking, self).write(vals)
        if 'location_id' in vals or 'location_dest_id' in vals:
            self._check_user_location_restrictions()
        return res

class InheritStockLocation(models.Model):
    _inherit="stock.location"
    
    @api.model
    def search_fetch(self, domain, field_names, offset=0, limit=None, order=None):
        domain = domain or []
        allowed_access = self.env.user.has_group('bi_warehouse_restrictions.group_restrict_operations')
        current_uid = self._context.get('uid')
        user = self.env['res.users'].browse(current_uid)
        final_location_ids = user.location_ids
    
        if user.restrict_location and allowed_access:
            domain += [('id','in',final_location_ids.ids)]
            
        return super(InheritStockLocation, self).search_fetch(domain, field_names, offset, limit, order)

    @api.model
    def _name_search(self, name, domain=None, operator='ilike', limit=None, order=None):
        domain = domain or []
        allowed_access = self.env.user.has_group('bi_warehouse_restrictions.group_restrict_operations')
        current_uid = self._context.get('uid')
        user = self.env['res.users'].browse(current_uid)
        final_location_ids = user.location_ids
    
        if user.restrict_location and allowed_access:
            domain += [('id','in',final_location_ids.ids)]
            
        return super(InheritStockLocation, self)._name_search(name, domain, operator, limit, order)


class InheritStockWarehouse(models.Model):
    _inherit="stock.warehouse"

    @api.model
    def search_fetch(self, domain, field_names, offset=0, limit=None, order=None):
        domain = domain or []
        allowed_access = self.env.user.has_group('bi_warehouse_restrictions.group_restrict_operations')
        current_uid = self._context.get('uid')
        user = self.env['res.users'].browse(current_uid)
        final_warehouse_ids = user.warehouse_ids
    
        if user.restrict_warehouse_list and allowed_access:
            domain += [('id','in',final_warehouse_ids.ids)]

        return super(InheritStockWarehouse, self).search_fetch(domain, field_names, offset, limit, order)

    @api.model
    def _name_search(self, name, domain=None, operator='ilike', limit=None, order=None):
        context = dict(self.env.context)
        domain = domain or []
        allowed_access = self.env.user.has_group('bi_warehouse_restrictions.group_restrict_operations')
        current_uid = self._context.get('uid')
        user = self.env['res.users'].browse(current_uid)
        final_warehouse_ids = user.warehouse_ids
    
        if user.restrict_warehouse_list and allowed_access:
            domain += [('id','in',final_warehouse_ids.ids)]

        return super(InheritStockWarehouse, self.sudo().with_context(context))._name_search(name, domain, operator, limit, order)


class InheritMrpProduction(models.Model):
    _inherit = "mrp.production"

    def _check_user_component_location_restrictions(self):
        current_user = self.env.user

        for production in self:
            if production.location_src_id and current_user.allowed_component_locations_ids and production.location_src_id not in current_user.allowed_component_locations_ids:
                raise ValidationError(_(
                    "You are not allowed to use '%s' as the Component Source Location (Source Location on MO) for this Manufacturing Order."
                ) % production.location_src_id.display_name)

    @api.model_create_multi
    def create(self, vals_list):
        productions = super().create(vals_list)
        productions._check_user_component_location_restrictions()
        return productions

    def write(self, vals):
        if 'location_src_id' in vals or vals.get('state') in ('planned', 'progress'):
            self._check_user_component_location_restrictions()
        return super().write(vals)
