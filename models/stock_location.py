# -*- coding: utf-8 -*-
# Part of Browseinfo. See LICENSE file for full copyright and licensing details.


from odoo import api, fields, models,_
from odoo.osv import expression


class InheritStockLocation(models.Model):
    _inherit = 'stock.location'

    user_count = fields.Integer(
        string='Associated Users',
        compute='_compute_user_count',
        help="The number of users who have this location in their restrictions."
    )

    def should_bypass_reservation(self):
        self.ensure_one()
        allowed_access = self.env.user.has_group('bi_warehouse_restrictions.group_restrict_operations')
        current_uid = self._context.get('uid')
        user = self.env['res.users'].browse(current_uid)

        if allowed_access and user.restrict_operation and user.restrict_location and self.usage == 'internal':
            return self.usage in ('supplier', 'customer', 'inventory', 'production', 'internal') or self.scrap_location or (self.usage == 'transit' and not self.company_id)

        return self.usage in ('supplier', 'customer', 'inventory', 'production') or self.scrap_location or (self.usage == 'transit' and not self.company_id)

    def _compute_user_count(self):
        """
        Computes the number of users who have this location in any of the three
        restricted fields (Source, Destination, Component).
        """
        for location in self:
            users = self.env['res.users'].search([
                '|', '|',
                ('allowed_source_locations_ids', 'in', location.id),
                ('allowed_destination_locations_ids', 'in', location.id),
                ('allowed_component_locations_ids', 'in', location.id),
            ])
            location.user_count = len(users)

    def action_view_associated_users(self):
        """
        Smart button action to view the list of users associated with this location.
        """
        self.ensure_one()
        return {
            'name': _('Users Restricted to %s', self.display_name),
            'view_mode': 'tree,form',
            'res_model': 'res.users',
            'type': 'ir.actions.act_window',
            'domain': [
                '|', '|',
                ('allowed_source_locations_ids', 'in', self.id),
                ('allowed_destination_locations_ids', 'in', self.id),
                ('allowed_component_locations_ids', 'in', self.id),
            ],
            'context': {'default_groups_ref': ['base.group_user']},
        }