# -*- coding: utf-8 -*-
"""扫码出入库业务逻辑：条码识别 + 生成并过账库存调拨"""
from odoo import api, models
from odoo.exceptions import UserError


class OdkScan(models.TransientModel):
    _name = "odk.scan"
    _description = "奥登科·扫码出入库助手"

    @api.model
    def act_warehouses(self):
        """给页面提供仓库下拉数据"""
        recs = self.env["stock.warehouse"].search([])
        return [{"id": w.id, "name": w.name, "code": w.code} for w in recs]

    @api.model
    def act_lookup(self, barcode):
        """条码 / 物料编码 → 物料信息（找不到返回空字典）"""
        barcode = (barcode or "").strip()
        if not barcode:
            return {}
        rec = self.env["product.product"].search(
            ["|", ("barcode", "=", barcode), ("default_code", "=", barcode)], limit=1)
        if not rec:
            return {}
        return {
            "id": rec.id,
            "name": rec.name,
            "code": rec.default_code or "",
            "uom": rec.uom_id.name or "",
            "barcode": rec.barcode or "",
        }

    @api.model
    def act_transfer(self, barcode, qty, from_id, to_id, fo_ref=""):
        """生成并过账一张内部调拨单：from 仓库 → to 仓库"""
        barcode = (barcode or "").strip()
        qty = float(qty or 0)
        if not barcode:
            raise UserError("请先扫描或输入条码")
        if qty <= 0:
            raise UserError("数量必须大于 0")
        product = self.env["product.product"].search(
            ["|", ("barcode", "=", barcode), ("default_code", "=", barcode)], limit=1)
        if not product:
            raise UserError("条码未找到对应物料：" + barcode)
        wh_from = self.env["stock.warehouse"].browse(int(from_id)).exists()
        wh_to = self.env["stock.warehouse"].browse(int(to_id)).exists()
        if not wh_from or not wh_to:
            raise UserError("请选择源仓库和目标仓库")
        if wh_from.id == wh_to.id:
            raise UserError("源仓库与目标仓库不能相同")
        picking_type = self.env["stock.picking.type"].search(
            [("code", "=", "internal"), ("warehouse_id", "=", wh_from.id)], limit=1)
        if not picking_type:
            raise UserError("仓库 %s 未配置内部调拨单据类型" % wh_from.name)
        picking = self.env["stock.picking"].create({
            "picking_type_id": picking_type.id,
            "location_id": wh_from.lot_stock_id.id,
            "location_dest_id": wh_to.lot_stock_id.id,
            "origin": (fo_ref or "")[:64],
            "move_ids": [(0, 0, {
                "description_picking": product.display_name,
                "product_id": product.id,
                "product_uom_qty": qty,
                "uom_id": product.uom_id.id,
                "location_id": wh_from.lot_stock_id.id,
                "location_dest_id": wh_to.lot_stock_id.id,
            })],
        })
        picking.action_confirm()
        # v17+：quantity 为已完成数量，picked=True 表示拣货完成
        for move in picking.move_ids:
            move.write({"quantity": qty, "picked": True})
        picking.with_context(skip_backorder=True, cancel_backorder=True).button_validate()
        picking.invalidate_recordset()
        return {"name": picking.name, "state": picking.state}
