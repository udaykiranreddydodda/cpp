"""
stock_id.py - Stock ID generation and parsing utilities.
"""

import uuid
import random
import string
from datetime import datetime


class StockIDGenerator:
    """Generates and parses unique identifiers for inventory operations."""

    @staticmethod
    def generate_movement_id(product_id, warehouse="WH01"):
        """
        Generate a unique movement ID.

        Format: MOV-{warehouse}-{product_id[:8]}-{timestamp}-{random4}

        Args:
            product_id (str): The product identifier.
            warehouse (str): Warehouse code, defaults to 'WH01'.

        Returns:
            str: A unique movement ID string.
        """
        timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
        rand4 = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
        product_ref = product_id[:8].upper()
        return f"MOV-{warehouse}-{product_ref}-{timestamp}-{rand4}"

    @staticmethod
    def generate_product_sku(category, name):
        """
        Generate a product SKU.

        Format: SKU-{CAT[:3]}-{NAME[:4]}-{random6} (all uppercase)

        Args:
            category (str): Product category.
            name (str): Product name.

        Returns:
            str: A unique SKU string.
        """
        cat_part = category[:3].upper()
        name_part = name[:4].upper()
        rand6 = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
        return f"SKU-{cat_part}-{name_part}-{rand6}"

    @staticmethod
    def generate_batch_id():
        """
        Generate a batch ID.

        Format: BATCH-{YYYYMMDD}-{random6}

        Returns:
            str: A unique batch ID string.
        """
        date_str = datetime.utcnow().strftime("%Y%m%d")
        rand6 = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
        return f"BATCH-{date_str}-{rand6}"

    @staticmethod
    def parse_movement_id(movement_id):
        """
        Parse a movement ID into its components.

        Args:
            movement_id (str): A movement ID string in the expected format.

        Returns:
            dict: Dictionary with 'warehouse', 'product_ref', and 'timestamp' keys.

        Raises:
            ValueError: If the movement ID format is invalid.
        """
        parts = movement_id.split("-")
        if len(parts) != 5 or parts[0] != "MOV":
            raise ValueError(f"Invalid movement ID format: {movement_id}")

        return {
            "warehouse": parts[1],
            "product_ref": parts[2],
            "timestamp": parts[3],
        }
