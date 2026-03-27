"""
reorder.py - Reorder management and stock alerting.
"""

from datetime import datetime


class ReorderManager:
    """Manages reorder logic, alerts, and purchase order generation."""

    @staticmethod
    def check_low_stock(products, threshold_pct=20):
        """
        Identify products that are low on stock.

        A product is considered low stock if:
            - currentStock < minStock, OR
            - currentStock < maxStock * threshold_pct / 100

        Args:
            products (list[dict]): List of product dictionaries.
            threshold_pct (int): Percentage threshold of maxStock.

        Returns:
            list[dict]: Products that need reordering.
        """
        low = []
        for p in products:
            current = p.get("currentStock", 0)
            min_stock = p.get("minStock", 0)
            max_stock = p.get("maxStock", 0)
            threshold = max_stock * threshold_pct / 100

            if current < min_stock or current < threshold:
                low.append(p)
        return low

    @staticmethod
    def generate_reorder_alert(product):
        """
        Generate a formatted reorder alert string for a product.

        Args:
            product (dict): Product dictionary with name, sku, currentStock,
                            minStock, and supplier keys.

        Returns:
            str: Formatted alert message.
        """
        name = product.get("name", "Unknown")
        sku = product.get("sku", "N/A")
        current = product.get("currentStock", 0)
        min_stock = product.get("minStock", 0)
        supplier = product.get("supplier", "Unknown Supplier")
        reorder_qty = max(0, min_stock - current)

        return (
            f"LOW STOCK ALERT: {name} (SKU: {sku}) - "
            f"Current: {current}/{min_stock} units. "
            f"Reorder {reorder_qty} units from {supplier}."
        )

    @staticmethod
    def calculate_reorder_quantity(product):
        """
        Calculate how many units to reorder to reach maxStock.

        Args:
            product (dict): Product dictionary with currentStock and maxStock.

        Returns:
            int: Number of units to reorder.
        """
        max_stock = product.get("maxStock", 0)
        current = product.get("currentStock", 0)
        return max(0, max_stock - current)

    @staticmethod
    def generate_purchase_order(products):
        """
        Generate a formatted purchase order text for a list of products.

        Args:
            products (list[dict]): Products that need reordering.

        Returns:
            str: Formatted purchase order text.
        """
        now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
        lines = []
        lines.append("=" * 55)
        lines.append("           PURCHASE ORDER")
        lines.append(f"  Generated: {now}")
        lines.append("=" * 55)
        lines.append("")

        total_cost = 0.0
        for i, p in enumerate(products, 1):
            name = p.get("name", "Unknown")
            sku = p.get("sku", "N/A")
            price = p.get("price", 0)
            max_stock = p.get("maxStock", 0)
            current = p.get("currentStock", 0)
            qty = max(0, max_stock - current)
            line_cost = qty * price
            total_cost += line_cost

            lines.append(f"  {i}. {name} (SKU: {sku})")
            lines.append(f"     Quantity: {qty} units @ ${price:.2f} each")
            lines.append(f"     Line Total: ${line_cost:.2f}")
            lines.append("")

        lines.append("-" * 55)
        lines.append(f"  TOTAL ESTIMATED COST: ${total_cost:.2f}")
        lines.append("=" * 55)

        return "\n".join(lines)

    @staticmethod
    def get_stock_status(product):
        """
        Determine the stock status of a product.

        Returns:
            - 'critical' if currentStock < 10% of maxStock
            - 'low' if currentStock < 25% of maxStock
            - 'normal' if currentStock is 25-75% of maxStock
            - 'full' if currentStock > 75% of maxStock

        Args:
            product (dict): Product dictionary with currentStock and maxStock.

        Returns:
            str: One of 'critical', 'low', 'normal', 'full'.
        """
        current = product.get("currentStock", 0)
        max_stock = product.get("maxStock", 1)

        if max_stock <= 0:
            return "critical"

        ratio = current / max_stock

        if ratio < 0.10:
            return "critical"
        elif ratio < 0.25:
            return "low"
        elif ratio <= 0.75:
            return "normal"
        else:
            return "full"
