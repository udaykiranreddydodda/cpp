"""
validator.py - Input validation for inventory data.
"""

import re


VALID_CATEGORIES = [
    "electronics",
    "clothing",
    "food",
    "furniture",
    "tools",
    "office",
    "other",
]


class InventoryValidator:
    """Validates and sanitizes inventory-related data."""

    @staticmethod
    def validate_product(data):
        """
        Validate product data.

        Checks:
            - name: required, 2-100 characters
            - sku: required, alphanumeric + dash only
            - category: must be in allowed list
            - price: must be a number > 0
            - minStock: must be >= 0
            - maxStock: must be > minStock

        Args:
            data (dict): Product data dictionary.

        Returns:
            tuple: (is_valid: bool, errors: list[str])
        """
        errors = []

        # name
        name = data.get("name")
        if not name or not isinstance(name, str):
            errors.append("Name is required and must be a string.")
        elif len(name.strip()) < 2 or len(name.strip()) > 100:
            errors.append("Name must be between 2 and 100 characters.")

        # sku
        sku = data.get("sku")
        if not sku or not isinstance(sku, str):
            errors.append("SKU is required and must be a string.")
        elif not re.match(r'^[A-Za-z0-9\-]+$', sku):
            errors.append("SKU must contain only alphanumeric characters and dashes.")

        # category
        category = data.get("category")
        if category not in VALID_CATEGORIES:
            errors.append(
                f"Category must be one of: {', '.join(VALID_CATEGORIES)}."
            )

        # price
        price = data.get("price")
        if not isinstance(price, (int, float)) or price <= 0:
            errors.append("Price must be a number greater than 0.")

        # minStock
        min_stock = data.get("minStock")
        if not isinstance(min_stock, (int, float)) or min_stock < 0:
            errors.append("minStock must be a number >= 0.")

        # maxStock
        max_stock = data.get("maxStock")
        if not isinstance(max_stock, (int, float)):
            errors.append("maxStock must be a number.")
        elif isinstance(min_stock, (int, float)) and max_stock <= min_stock:
            errors.append("maxStock must be greater than minStock.")

        return (len(errors) == 0, errors)

    @staticmethod
    def validate_stock_movement(data):
        """
        Validate stock movement data.

        Checks:
            - type: must be 'intake' or 'dispatch'
            - quantity: must be a positive integer
            - reference: optional, must be a string if provided

        Args:
            data (dict): Stock movement data dictionary.

        Returns:
            tuple: (is_valid: bool, errors: list[str])
        """
        errors = []

        move_type = data.get("type")
        if move_type not in ("intake", "dispatch"):
            errors.append("Type must be 'intake' or 'dispatch'.")

        quantity = data.get("quantity")
        if not isinstance(quantity, int) or quantity <= 0:
            errors.append("Quantity must be a positive integer.")

        reference = data.get("reference")
        if reference is not None and not isinstance(reference, str):
            errors.append("Reference must be a string if provided.")

        return (len(errors) == 0, errors)

    @staticmethod
    def validate_supplier(data):
        """
        Validate supplier data.

        Checks:
            - name: required string
            - email: must contain '@'

        Args:
            data (dict): Supplier data dictionary.

        Returns:
            tuple: (is_valid: bool, errors: list[str])
        """
        errors = []

        name = data.get("name")
        if not name or not isinstance(name, str) or len(name.strip()) == 0:
            errors.append("Supplier name is required.")

        email = data.get("email")
        if not email or not isinstance(email, str) or "@" not in email:
            errors.append("A valid email address with '@' is required.")

        return (len(errors) == 0, errors)

    @staticmethod
    def sanitize_input(text):
        """
        Strip HTML tags from input text.

        Args:
            text (str): Raw input text.

        Returns:
            str: Text with HTML tags removed.
        """
        return re.sub(r'<[^>]+>', '', text)

    @staticmethod
    def validate_quantity_available(current_stock, dispatch_quantity):
        """
        Check if there is sufficient stock for a dispatch.

        Args:
            current_stock (int): Current stock level.
            dispatch_quantity (int): Quantity to dispatch.

        Returns:
            tuple: (is_valid: bool, error_msg: str or None)
        """
        if dispatch_quantity > current_stock:
            return (
                False,
                f"Insufficient stock: requested {dispatch_quantity} but only {current_stock} available.",
            )
        return (True, None)
