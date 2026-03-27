"""
inventory_manager - Smart Inventory Management System Library
A PyPI-publishable OOP library for inventory management operations.
"""

__version__ = "1.0.0"
__author__ = "Uday Kiran Reddy Dodda"

from inventory_manager.stock_id import StockIDGenerator
from inventory_manager.validator import InventoryValidator
from inventory_manager.reorder import ReorderManager
from inventory_manager.formatter import InventoryFormatter

__all__ = [
    "StockIDGenerator",
    "InventoryValidator",
    "ReorderManager",
    "InventoryFormatter",
]
