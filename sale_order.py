from odoo import models, fields, api,_
from odoo.exceptions import UserError

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    manager_reference = fields.Char(string='Manager Reference')
    edit_manager_ref=fields.Boolean(string="edit_manager_reference",compute="_compute_edit_manager_reference",store= False)
    auto_workflow = fields.Boolean(string="Auto Workflow")
    
   
    @api.depends('manager_reference')
    def _compute_edit_manager_reference(self):
        for record in self:
            record.edit_manager_ref=self.env.user.has_group('Test.group_sale_admin')
            
    @api.model
    def _get_sale_order_limit(self):
        limit = self.env['ir.config_parameter'].sudo().get_param('sale.order_limit', default='0.0')
        return float(limit)
    
   


    def action_confirm(self):
        limit = self._get_sale_order_limit()
        user = self.env.user
        sale_admin_group = self.env.ref('Test.group_sale_admin', raise_if_not_found=False)

        for order in self:
            if order.amount_total > limit:
                if not sale_admin_group or sale_admin_group not in user.groups_id:
                    raise UserError(_("Sale order exceeds the allowed limit. Please contact the Sales Admin."))

        result = super(SaleOrder, self).action_confirm()
        
        for order in self.filtered(lambda o: o.auto_workflow):
            self._process_auto_workflow(order)
            
        return result
    
    def _process_auto_workflow(self, order):
        try:
            self._process_auto_deliveries(order)
            
            invoice = self._create_auto_invoice(order)
            
            self._register_auto_payment(invoice)
            
        except Exception as e:
            raise UserError(_(f"Auto workflow processing failed: {str(e)}"))
    
    def _process_auto_deliveries(self, order):
        pickings = self.env['stock.picking'].search([
            ('sale_id', '=', order.id),
            ('state', 'not in', ['done', 'cancel'])
        ])
        
        if not pickings:
            return
            
        for picking in pickings:
            if picking.state not in ['done', 'cancel']:
                picking.action_assign()
                
                for move in picking.move_ids:
                    if hasattr(move, 'quantity_done'):
                        move.quantity_done = move.product_uom_qty
                    elif hasattr(move, 'qty_done'):
                        move.qty_done = move.product_uom_qty
                    else:
                        for move_line in move.move_line_ids:
                            if hasattr(move_line, 'qty_done'):
                                move_line.qty_done = move_line.product_qty or move_line.reserved_qty or 0
                
                try:
                    if hasattr(picking, 'button_validate'):
                        picking.button_validate()
                    else:
                        picking.action_done()
                except Exception as e:
                    order.message_post(body=_(f"Delivery validation failed for picking {picking.name}: {str(e)}"))
    
    def _create_auto_invoice(self, order):
        invoice = order._create_invoices()
        
        invoice.action_post()
        
        return invoice
    
    def _register_auto_payment(self, invoice):
        payment_register = self.env['account.payment.register'].with_context(
            active_model='account.move',
            active_ids=invoice.ids
        ).create({
            'payment_date': fields.Date.today(),
            'journal_id': self.env['account.journal'].search([
                ('type', 'in', ['bank', 'cash']),
                ('company_id', '=', invoice.company_id.id)
            ], limit=1).id,
            'amount': invoice.amount_residual,
        })
        
        payment_register._create_payments()
