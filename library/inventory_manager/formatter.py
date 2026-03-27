"""
formatter.py - Formatting utilities for inventory reports and exports.
"""

import csv
import io
from datetime import datetime

from inventory_manager.reorder import ReorderManager


class InventoryFormatter:
    """Formats inventory data for display, reports, and export."""

    @staticmethod
    def format_product_summary(product):
        """
        Format a single product as a one-line summary.

        Format: "SKU: {sku} | {name} | Stock: {current}/{max} | ${price}"

        Args:
            product (dict): Product dictionary.

        Returns:
            str: One-line summary string.
        """
        sku = product.get("sku", "N/A")
        name = product.get("name", "Unknown")
        current = product.get("currentStock", 0)
        max_stock = product.get("maxStock", 0)
        price = product.get("price", 0)
        return f"SKU: {sku} | {name} | Stock: {current}/{max_stock} | ${price:.2f}"

    @staticmethod
    def format_stock_report(products):
        """
        Format a multi-line stock report with headers, totals, and status.

        Args:
            products (list[dict]): List of product dictionaries.

        Returns:
            str: Formatted stock report.
        """
        now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
        lines = []
        lines.append("=" * 70)
        lines.append("                    STOCK REPORT")
        lines.append(f"  Generated: {now}")
        lines.append("=" * 70)
        lines.append("")
        lines.append(
            f"  {'Name':<25} {'SKU':<20} {'Stock':>10} {'Status':>10}"
        )
        lines.append("  " + "-" * 65)

        total_value = 0.0
        for p in products:
            name = p.get("name", "Unknown")[:25]
            sku = p.get("sku", "N/A")[:20]
            current = p.get("currentStock", 0)
            max_stock = p.get("maxStock", 0)
            price = p.get("price", 0)
            status = ReorderManager.get_stock_status(p)
            total_value += current * price
            stock_str = f"{current}/{max_stock}"
            lines.append(
                f"  {name:<25} {sku:<20} {stock_str:>10} {status:>10}"
            )

        lines.append("")
        lines.append("-" * 70)
        lines.append(f"  Total Products: {len(products)}")
        lines.append(f"  Total Inventory Value: ${total_value:,.2f}")
        lines.append("=" * 70)

        return "\n".join(lines)

    @staticmethod
    def format_movement_log(movements):
        """
        Format a log of stock movements.

        Each movement dict should have: type, quantity, product_name,
        timestamp (ISO string), and optionally reference.

        Args:
            movements (list[dict]): List of movement dictionaries.

        Returns:
            str: Formatted movement log.
        """
        lines = []
        lines.append("=" * 60)
        lines.append("              STOCK MOVEMENT LOG")
        lines.append("=" * 60)
        lines.append("")

        for m in movements:
            move_type = m.get("type", "unknown").upper()
            qty = m.get("quantity", 0)
            product = m.get("product_name", "Unknown")
            timestamp = m.get("timestamp", "N/A")
            reference = m.get("reference", "")

            direction = "IN " if move_type == "INTAKE" else "OUT"
            line = f"  [{timestamp}] {direction} {qty:>6} x {product} ({move_type})"
            if reference:
                line += f" - Ref: {reference}"
            lines.append(line)

        lines.append("")
        lines.append("=" * 60)
        return "\n".join(lines)

    @staticmethod
    def to_csv(products):
        """
        Convert product list to CSV string.

        Headers: name, sku, category, price, currentStock, minStock, maxStock, status

        Args:
            products (list[dict]): List of product dictionaries.

        Returns:
            str: CSV-formatted string.
        """
        output = io.StringIO()
        fieldnames = [
            "name", "sku", "category", "price",
            "currentStock", "minStock", "maxStock", "status",
        ]
        writer = csv.DictWriter(output, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()

        for p in products:
            row = {k: p.get(k, "") for k in fieldnames}
            row["status"] = ReorderManager.get_stock_status(p)
            writer.writerow(row)

        return output.getvalue()

    @staticmethod
    def format_dashboard_stats(products):
        """
        Generate dashboard statistics from a product list.

        Returns:
            dict: {
                total_products, total_value, low_stock_count,
                categories: {category: count, ...}
            }
        """
        total_value = 0.0
        low_stock_count = 0
        categories = {}

        for p in products:
            current = p.get("currentStock", 0)
            price = p.get("price", 0)
            total_value += current * price

            status = ReorderManager.get_stock_status(p)
            if status in ("critical", "low"):
                low_stock_count += 1

            cat = p.get("category", "other")
            categories[cat] = categories.get(cat, 0) + 1

        return {
            "total_products": len(products),
            "total_value": round(total_value, 2),
            "low_stock_count": low_stock_count,
            "categories": categories,
        }
