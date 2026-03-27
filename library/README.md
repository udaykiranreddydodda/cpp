# inventory-manager-nci

A Python library for Smart Inventory Management operations. Provides stock ID generation, data validation, reorder management, and reporting utilities.

## Installation

```bash
pip install inventory-manager-nci
```

## Usage

```python
from inventory_manager import StockIDGenerator, InventoryValidator, ReorderManager, InventoryFormatter

# Generate a product SKU
sku = StockIDGenerator.generate_product_sku("electronics", "mouse")

# Validate product data
valid, errors = InventoryValidator.validate_product({
    "name": "Wireless Mouse",
    "sku": sku,
    "category": "electronics",
    "price": 29.99,
    "minStock": 20,
    "maxStock": 200,
})

# Check stock status
status = ReorderManager.get_stock_status(product)

# Export to CSV
csv_data = InventoryFormatter.to_csv(products)
```

## Modules

- **StockIDGenerator** - Generate movement IDs, SKUs, and batch IDs
- **InventoryValidator** - Validate products, stock movements, and suppliers
- **ReorderManager** - Low stock detection, alerts, and purchase orders
- **InventoryFormatter** - Reports, CSV export, and dashboard statistics

## Author

Uday Kiran Reddy Dodda
