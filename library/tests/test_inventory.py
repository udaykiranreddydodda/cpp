"""
Unit tests for the inventory_manager library.
"""

import unittest
import sys
import os

# Ensure the library root is on the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from inventory_manager.stock_id import StockIDGenerator
from inventory_manager.validator import InventoryValidator
from inventory_manager.reorder import ReorderManager
from inventory_manager.formatter import InventoryFormatter


# ---------------------------------------------------------------------------
# Sample data helpers
# ---------------------------------------------------------------------------

def _sample_product(**overrides):
    base = {
        "name": "Wireless Mouse",
        "sku": "SKU-ELE-WIRE-ABC123",
        "category": "electronics",
        "price": 29.99,
        "currentStock": 50,
        "minStock": 20,
        "maxStock": 200,
        "supplier": "TechSupplies Co.",
    }
    base.update(overrides)
    return base


def _sample_movement(**overrides):
    base = {
        "type": "intake",
        "quantity": 100,
        "product_name": "Wireless Mouse",
        "timestamp": "2026-03-28T10:00:00Z",
        "reference": "PO-001",
    }
    base.update(overrides)
    return base


# ===========================================================================
# StockIDGenerator Tests
# ===========================================================================

class TestStockIDGenerator(unittest.TestCase):

    def test_movement_id_format(self):
        mid = StockIDGenerator.generate_movement_id("prod12345678extra")
        self.assertTrue(mid.startswith("MOV-WH01-"))
        parts = mid.split("-")
        self.assertEqual(len(parts), 5)
        self.assertEqual(parts[0], "MOV")
        self.assertEqual(parts[1], "WH01")

    def test_movement_id_custom_warehouse(self):
        mid = StockIDGenerator.generate_movement_id("abc", warehouse="WH99")
        self.assertIn("WH99", mid)

    def test_movement_id_product_ref_truncated(self):
        mid = StockIDGenerator.generate_movement_id("longproductid1234")
        product_ref = mid.split("-")[2]
        self.assertEqual(len(product_ref), 8)

    def test_sku_format(self):
        sku = StockIDGenerator.generate_product_sku("electronics", "mouse")
        self.assertTrue(sku.startswith("SKU-ELE-MOUS-"))
        self.assertEqual(sku, sku.upper())

    def test_sku_short_name(self):
        sku = StockIDGenerator.generate_product_sku("food", "ab")
        self.assertTrue(sku.startswith("SKU-FOO-AB-"))

    def test_batch_id_format(self):
        bid = StockIDGenerator.generate_batch_id()
        self.assertTrue(bid.startswith("BATCH-"))
        parts = bid.split("-")
        self.assertEqual(len(parts), 3)
        self.assertEqual(len(parts[1]), 8)  # YYYYMMDD

    def test_parse_movement_id_valid(self):
        mid = StockIDGenerator.generate_movement_id("testprod")
        parsed = StockIDGenerator.parse_movement_id(mid)
        self.assertIn("warehouse", parsed)
        self.assertIn("product_ref", parsed)
        self.assertIn("timestamp", parsed)
        self.assertEqual(parsed["warehouse"], "WH01")

    def test_parse_movement_id_invalid(self):
        with self.assertRaises(ValueError):
            StockIDGenerator.parse_movement_id("INVALID-ID")

    def test_movement_ids_unique(self):
        ids = {StockIDGenerator.generate_movement_id("p1") for _ in range(50)}
        self.assertEqual(len(ids), 50)


# ===========================================================================
# InventoryValidator Tests
# ===========================================================================

class TestInventoryValidator(unittest.TestCase):

    def test_valid_product(self):
        valid, errors = InventoryValidator.validate_product(_sample_product())
        self.assertTrue(valid)
        self.assertEqual(errors, [])

    def test_product_missing_name(self):
        valid, errors = InventoryValidator.validate_product(_sample_product(name=""))
        self.assertFalse(valid)
        self.assertTrue(any("Name" in e for e in errors))

    def test_product_name_too_short(self):
        valid, errors = InventoryValidator.validate_product(_sample_product(name="A"))
        self.assertFalse(valid)

    def test_product_bad_sku(self):
        valid, errors = InventoryValidator.validate_product(_sample_product(sku="BAD SKU!"))
        self.assertFalse(valid)
        self.assertTrue(any("SKU" in e for e in errors))

    def test_product_bad_category(self):
        valid, errors = InventoryValidator.validate_product(_sample_product(category="weapons"))
        self.assertFalse(valid)

    def test_product_negative_price(self):
        valid, errors = InventoryValidator.validate_product(_sample_product(price=-5))
        self.assertFalse(valid)

    def test_product_maxstock_less_than_minstock(self):
        valid, errors = InventoryValidator.validate_product(
            _sample_product(minStock=100, maxStock=50)
        )
        self.assertFalse(valid)

    def test_valid_stock_movement(self):
        valid, errors = InventoryValidator.validate_stock_movement(
            {"type": "intake", "quantity": 10}
        )
        self.assertTrue(valid)

    def test_invalid_movement_type(self):
        valid, errors = InventoryValidator.validate_stock_movement(
            {"type": "transfer", "quantity": 10}
        )
        self.assertFalse(valid)

    def test_movement_zero_quantity(self):
        valid, errors = InventoryValidator.validate_stock_movement(
            {"type": "dispatch", "quantity": 0}
        )
        self.assertFalse(valid)

    def test_movement_float_quantity(self):
        valid, errors = InventoryValidator.validate_stock_movement(
            {"type": "intake", "quantity": 5.5}
        )
        self.assertFalse(valid)

    def test_valid_supplier(self):
        valid, errors = InventoryValidator.validate_supplier(
            {"name": "ACME Corp", "email": "info@acme.com"}
        )
        self.assertTrue(valid)

    def test_supplier_missing_email(self):
        valid, errors = InventoryValidator.validate_supplier(
            {"name": "ACME Corp", "email": "noemail"}
        )
        self.assertFalse(valid)

    def test_sanitize_input(self):
        result = InventoryValidator.sanitize_input("<b>bold</b> & <script>alert('x')</script>safe")
        self.assertEqual(result, "bold & alert('x')safe")

    def test_quantity_available_ok(self):
        valid, msg = InventoryValidator.validate_quantity_available(100, 50)
        self.assertTrue(valid)
        self.assertIsNone(msg)

    def test_quantity_available_fail(self):
        valid, msg = InventoryValidator.validate_quantity_available(10, 50)
        self.assertFalse(valid)
        self.assertIn("Insufficient", msg)


# ===========================================================================
# ReorderManager Tests
# ===========================================================================

class TestReorderManager(unittest.TestCase):

    def test_check_low_stock_detects_below_min(self):
        products = [_sample_product(currentStock=5, minStock=20)]
        low = ReorderManager.check_low_stock(products)
        self.assertEqual(len(low), 1)

    def test_check_low_stock_threshold(self):
        # currentStock=30, maxStock=200 => 30 < 200*20/100=40 => low
        products = [_sample_product(currentStock=30)]
        low = ReorderManager.check_low_stock(products, threshold_pct=20)
        self.assertEqual(len(low), 1)

    def test_check_low_stock_ok(self):
        products = [_sample_product(currentStock=150)]
        low = ReorderManager.check_low_stock(products)
        self.assertEqual(len(low), 0)

    def test_generate_reorder_alert(self):
        alert = ReorderManager.generate_reorder_alert(_sample_product(currentStock=5))
        self.assertIn("LOW STOCK ALERT", alert)
        self.assertIn("Wireless Mouse", alert)
        self.assertIn("15 units", alert)  # 20 - 5

    def test_calculate_reorder_quantity(self):
        qty = ReorderManager.calculate_reorder_quantity(
            _sample_product(currentStock=50, maxStock=200)
        )
        self.assertEqual(qty, 150)

    def test_generate_purchase_order(self):
        po = ReorderManager.generate_purchase_order([_sample_product(currentStock=10)])
        self.assertIn("PURCHASE ORDER", po)
        self.assertIn("Wireless Mouse", po)
        self.assertIn("TOTAL ESTIMATED COST", po)

    def test_stock_status_critical(self):
        self.assertEqual(
            ReorderManager.get_stock_status(_sample_product(currentStock=1, maxStock=100)),
            "critical",
        )

    def test_stock_status_low(self):
        self.assertEqual(
            ReorderManager.get_stock_status(_sample_product(currentStock=20, maxStock=100)),
            "low",
        )

    def test_stock_status_normal(self):
        self.assertEqual(
            ReorderManager.get_stock_status(_sample_product(currentStock=50, maxStock=100)),
            "normal",
        )

    def test_stock_status_full(self):
        self.assertEqual(
            ReorderManager.get_stock_status(_sample_product(currentStock=80, maxStock=100)),
            "full",
        )


# ===========================================================================
# InventoryFormatter Tests
# ===========================================================================

class TestInventoryFormatter(unittest.TestCase):

    def test_format_product_summary(self):
        summary = InventoryFormatter.format_product_summary(_sample_product())
        self.assertIn("SKU:", summary)
        self.assertIn("Wireless Mouse", summary)
        self.assertIn("$29.99", summary)

    def test_format_stock_report(self):
        report = InventoryFormatter.format_stock_report([_sample_product()])
        self.assertIn("STOCK REPORT", report)
        self.assertIn("Total Products: 1", report)

    def test_format_movement_log(self):
        log = InventoryFormatter.format_movement_log([_sample_movement()])
        self.assertIn("STOCK MOVEMENT LOG", log)
        self.assertIn("Wireless Mouse", log)

    def test_to_csv_headers(self):
        csv_str = InventoryFormatter.to_csv([_sample_product()])
        first_line = csv_str.splitlines()[0]
        self.assertIn("name", first_line)
        self.assertIn("sku", first_line)
        self.assertIn("status", first_line)

    def test_to_csv_data_row(self):
        csv_str = InventoryFormatter.to_csv([_sample_product()])
        lines = csv_str.strip().splitlines()
        self.assertEqual(len(lines), 2)  # header + 1 row
        self.assertIn("Wireless Mouse", lines[1])

    def test_dashboard_stats_totals(self):
        products = [
            _sample_product(currentStock=50, price=10.0, category="electronics"),
            _sample_product(currentStock=20, price=5.0, category="clothing"),
        ]
        stats = InventoryFormatter.format_dashboard_stats(products)
        self.assertEqual(stats["total_products"], 2)
        self.assertEqual(stats["total_value"], 600.0)  # 50*10 + 20*5
        self.assertEqual(stats["categories"]["electronics"], 1)
        self.assertEqual(stats["categories"]["clothing"], 1)

    def test_dashboard_stats_low_stock_count(self):
        products = [
            _sample_product(currentStock=1, maxStock=100),   # critical
            _sample_product(currentStock=80, maxStock=100),  # full
        ]
        stats = InventoryFormatter.format_dashboard_stats(products)
        self.assertEqual(stats["low_stock_count"], 1)


if __name__ == "__main__":
    unittest.main()
