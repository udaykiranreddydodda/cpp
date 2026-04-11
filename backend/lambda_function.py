"""
Smart Inventory Management System — Lambda Backend
Single Lambda function handling all API routes.
DynamoDB single-table design with entityType discriminator.
"""

import json
import os
import uuid
import hashlib
import hmac
import base64
import time
from decimal import Decimal

import boto3
from boto3.dynamodb.conditions import Key, Attr

# ---------------------------------------------------------------------------
# Environment
# ---------------------------------------------------------------------------
TABLE_NAME = os.environ.get("DYNAMODB_TABLE", "smartinventory-prod")
S3_BUCKET = os.environ.get("S3_BUCKET", "smartinventory-files-prod-udaykiran")
SNS_TOPIC_ARN = os.environ.get("SNS_TOPIC_ARN", "")
REGION = os.environ.get("REGION", "eu-west-1")
JWT_SECRET = os.environ.get("JWT_SECRET", "smartinventory-secret-2026")

# AWS clients
dynamodb = boto3.resource("dynamodb", region_name=REGION)
table = dynamodb.Table(TABLE_NAME)
sns_client = boto3.client("sns", region_name=REGION)

# ---------------------------------------------------------------------------
# Helpers — CORS
# ---------------------------------------------------------------------------
CORS_HEADERS = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Headers": "Content-Type,Authorization",
    "Access-Control-Allow-Methods": "GET,POST,PUT,DELETE,OPTIONS",
}


def respond(status_code, body):
    """Build an API-Gateway-compatible response with CORS headers."""
    return {
        "statusCode": status_code,
        "headers": CORS_HEADERS,
        "body": json.dumps(body, default=str),
    }


# ---------------------------------------------------------------------------
# Helpers — DynamoDB Decimal conversion
# ---------------------------------------------------------------------------
def convert_to_decimal(obj):
    """Recursively convert floats/ints to Decimal for DynamoDB."""
    if isinstance(obj, float):
        return Decimal(str(obj))
    if isinstance(obj, int) and not isinstance(obj, bool):
        return Decimal(str(obj))
    if isinstance(obj, dict):
        return {k: convert_to_decimal(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [convert_to_decimal(i) for i in obj]
    return obj


# ---------------------------------------------------------------------------
# Helpers — Simple JWT (same pattern as other projects)
# ---------------------------------------------------------------------------
def _b64_encode(data: dict) -> str:
    return base64.urlsafe_b64encode(json.dumps(data).encode()).decode().rstrip("=")


def _b64_decode(s: str) -> dict:
    padding = 4 - len(s) % 4
    s += "=" * padding
    return json.loads(base64.urlsafe_b64decode(s))


def _sign(header_b64: str, payload_b64: str) -> str:
    msg = f"{header_b64}.{payload_b64}".encode()
    sig = hmac.new(JWT_SECRET.encode(), msg, hashlib.sha256).hexdigest()
    return sig


def create_token(user_id: str, email: str) -> str:
    """Create a simple JWT token."""
    header = _b64_encode({"alg": "HS256", "typ": "JWT"})
    payload = _b64_encode({
        "user_id": user_id,
        "email": email,
        "exp": int(time.time()) + 86400,  # 24 h
    })
    signature = _sign(header, payload)
    return f"{header}.{payload}.{signature}"


def verify_token(token: str) -> dict:
    """Verify a JWT token and return the payload or None."""
    try:
        parts = token.split(".")
        if len(parts) != 3:
            return None
        header_b64, payload_b64, signature = parts
        expected_sig = _sign(header_b64, payload_b64)
        if not hmac.compare_digest(expected_sig, signature):
            return None
        payload = _b64_decode(payload_b64)
        if payload.get("exp", 0) < int(time.time()):
            return None
        return payload
    except Exception:
        return None


def extract_user(headers: dict):
    """Extract and verify the user from the Authorization header."""
    auth = headers.get("Authorization") or headers.get("authorization", "")
    if not auth.startswith("Bearer "):
        return None
    token = auth.split(" ", 1)[1]
    return verify_token(token)


# ---------------------------------------------------------------------------
# Helpers — Password hashing
# ---------------------------------------------------------------------------
def hash_password(password: str) -> tuple:
    salt = os.urandom(16).hex()
    hashed = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 100000).hex()
    return hashed, salt


def verify_password(password: str, hashed: str, salt: str) -> bool:
    check = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 100000).hex()
    return hmac.compare_digest(check, hashed)


# ---------------------------------------------------------------------------
# Route handlers — Auth
# ---------------------------------------------------------------------------
def handle_register(body):
    """POST /auth/register — create a new user account."""
    username = body.get("username")
    email = body.get("email")
    password = body.get("password")
    if not all([username, email, password]):
        return respond(400, {"error": "username, email, and password are required"})

    # Check if email already exists
    try:
        result = table.scan(
            FilterExpression=Attr("entityType").eq("user") & Attr("email").eq(email)
        )
        if result.get("Items"):
            return respond(400, {"error": "Email already registered"})
    except Exception as e:
        return respond(500, {"error": f"Database error: {str(e)}"})

    hashed, salt = hash_password(password)
    user_id = str(uuid.uuid4())
    item = {
        "id": user_id,
        "entityType": "user",
        "username": username,
        "email": email,
        "password": hashed,
        "salt": salt,
        "createdAt": str(int(time.time())),
    }

    try:
        table.put_item(Item=convert_to_decimal(item))
    except Exception as e:
        return respond(500, {"error": f"Could not create user: {str(e)}"})

    token = create_token(user_id, email)
    return respond(201, {
        "message": "User registered successfully",
        "token": token,
        "user": {"id": user_id, "username": username, "email": email},
    })


def handle_login(body):
    """POST /auth/login — authenticate and return a token."""
    email = body.get("email")
    password = body.get("password")
    if not all([email, password]):
        return respond(400, {"error": "email and password are required"})

    try:
        result = table.scan(
            FilterExpression=Attr("entityType").eq("user") & Attr("email").eq(email)
        )
    except Exception as e:
        return respond(500, {"error": f"Database error: {str(e)}"})

    items = result.get("Items", [])
    if not items:
        return respond(401, {"error": "Invalid email or password"})

    user = items[0]
    if not verify_password(password, user["password"], user["salt"]):
        return respond(401, {"error": "Invalid email or password"})

    token = create_token(user["id"], user["email"])
    return respond(200, {
        "message": "Login successful",
        "token": token,
        "user": {"id": user["id"], "username": user["username"], "email": user["email"]},
    })


# ---------------------------------------------------------------------------
# Route handlers — Products (protected)
# ---------------------------------------------------------------------------
def handle_get_products():
    """GET /products — list all products."""
    try:
        result = table.scan(FilterExpression=Attr("entityType").eq("product"))
        return respond(200, {"products": result.get("Items", [])})
    except Exception as e:
        return respond(500, {"error": f"Could not fetch products: {str(e)}"})


def handle_create_product(body):
    """POST /products — create a new product."""
    required = ["name", "sku", "category"]
    if not all(body.get(f) for f in required):
        return respond(400, {"error": "name, sku, and category are required"})

    product_id = str(uuid.uuid4())
    item = {
        "id": product_id,
        "entityType": "product",
        "name": body.get("name"),
        "sku": body.get("sku"),
        "category": body.get("category"),
        "description": body.get("description", ""),
        "price": body.get("price", 0),
        "minStock": body.get("minStock", 0),
        "maxStock": body.get("maxStock", 0),
        "currentStock": body.get("currentStock", 0),
        "supplier": body.get("supplier", ""),
        "createdAt": str(int(time.time())),
        "updatedAt": str(int(time.time())),
    }

    try:
        table.put_item(Item=convert_to_decimal(item))
    except Exception as e:
        return respond(500, {"error": f"Could not create product: {str(e)}"})

    return respond(201, {"message": "Product created", "product": item})


def handle_get_product(product_id):
    """GET /products/{id} — get a single product."""
    try:
        result = table.get_item(Key={"id": product_id})
    except Exception as e:
        return respond(500, {"error": f"Database error: {str(e)}"})

    item = result.get("Item")
    if not item or item.get("entityType") != "product":
        return respond(404, {"error": "Product not found"})
    return respond(200, {"product": item})


def handle_update_product(product_id, body):
    """PUT /products/{id} — update product fields."""
    try:
        result = table.get_item(Key={"id": product_id})
    except Exception as e:
        return respond(500, {"error": f"Database error: {str(e)}"})

    item = result.get("Item")
    if not item or item.get("entityType") != "product":
        return respond(404, {"error": "Product not found"})

    allowed = ["name", "sku", "category", "description", "price",
               "minStock", "maxStock", "currentStock", "supplier"]
    update_expr_parts = []
    expr_values = {}
    expr_names = {}

    for field in allowed:
        if field in body:
            placeholder = f":val_{field}"
            name_placeholder = f"#field_{field}"
            update_expr_parts.append(f"{name_placeholder} = {placeholder}")
            expr_values[placeholder] = body[field]
            expr_names[name_placeholder] = field

    if not update_expr_parts:
        return respond(400, {"error": "No valid fields to update"})

    # Always update updatedAt
    update_expr_parts.append("#updatedAt = :updatedAt")
    expr_values[":updatedAt"] = str(int(time.time()))
    expr_names["#updatedAt"] = "updatedAt"

    try:
        table.update_item(
            Key={"id": product_id},
            UpdateExpression="SET " + ", ".join(update_expr_parts),
            ExpressionAttributeValues=convert_to_decimal(expr_values),
            ExpressionAttributeNames=expr_names,
        )
    except Exception as e:
        return respond(500, {"error": f"Could not update product: {str(e)}"})

    return respond(200, {"message": "Product updated"})


def handle_delete_product(product_id):
    """DELETE /products/{id} — delete a product."""
    try:
        result = table.get_item(Key={"id": product_id})
        item = result.get("Item")
        if not item or item.get("entityType") != "product":
            return respond(404, {"error": "Product not found"})
        table.delete_item(Key={"id": product_id})
    except Exception as e:
        return respond(500, {"error": f"Could not delete product: {str(e)}"})

    return respond(200, {"message": "Product deleted"})


# ---------------------------------------------------------------------------
# Route handlers — Stock Movements (protected)
# ---------------------------------------------------------------------------
def handle_create_stock_movement(product_id, body):
    """POST /products/{id}/stock — record a stock intake or dispatch."""
    movement_type = body.get("type", "").lower()
    quantity = body.get("quantity")
    if movement_type not in ("intake", "dispatch"):
        return respond(400, {"error": "type must be 'intake' or 'dispatch'"})
    if not quantity or int(quantity) <= 0:
        return respond(400, {"error": "quantity must be a positive number"})
    quantity = int(quantity)

    # Fetch the product
    try:
        result = table.get_item(Key={"id": product_id})
    except Exception as e:
        return respond(500, {"error": f"Database error: {str(e)}"})

    product = result.get("Item")
    if not product or product.get("entityType") != "product":
        return respond(404, {"error": "Product not found"})

    current_stock = int(product.get("currentStock", 0))

    # Validate dispatch has enough stock
    if movement_type == "dispatch":
        if quantity > current_stock:
            return respond(400, {
                "error": f"Insufficient stock. Available: {current_stock}, requested: {quantity}"
            })
        new_stock = current_stock - quantity
    else:
        new_stock = current_stock + quantity

    # Create movement record
    movement_id = str(uuid.uuid4())
    movement = {
        "id": movement_id,
        "entityType": "stockMovement",
        "productId": product_id,
        "productName": product.get("name", ""),
        "type": movement_type,
        "quantity": quantity,
        "previousStock": current_stock,
        "newStock": new_stock,
        "reference": body.get("reference", ""),
        "notes": body.get("notes", ""),
        "createdAt": str(int(time.time())),
    }

    try:
        table.put_item(Item=convert_to_decimal(movement))

        # Update product stock
        table.update_item(
            Key={"id": product_id},
            UpdateExpression="SET currentStock = :stock, updatedAt = :ts",
            ExpressionAttributeValues=convert_to_decimal({
                ":stock": new_stock,
                ":ts": str(int(time.time())),
            }),
        )
    except Exception as e:
        return respond(500, {"error": f"Could not record movement: {str(e)}"})

    # Check low-stock alert
    min_stock = int(product.get("minStock", 0))
    if new_stock < min_stock and SNS_TOPIC_ARN:
        try:
            sns_client.publish(
                TopicArn=SNS_TOPIC_ARN,
                Subject="Low Stock Alert — Smart Inventory",
                Message=(
                    f"Product '{product.get('name')}' (SKU: {product.get('sku')}) "
                    f"is below minimum stock level.\n"
                    f"Current stock: {new_stock}, Minimum: {min_stock}"
                ),
            )
        except Exception:
            pass  # Non-critical — don't fail the request

    return respond(201, {"message": "Stock movement recorded", "movement": movement})


def handle_get_stock_movements(product_id):
    """GET /products/{id}/stock — list stock movements for a product."""
    try:
        result = table.scan(
            FilterExpression=(
                Attr("entityType").eq("stockMovement") & Attr("productId").eq(product_id)
            )
        )
        items = sorted(result.get("Items", []), key=lambda x: x.get("createdAt", ""), reverse=True)
        return respond(200, {"movements": items})
    except Exception as e:
        return respond(500, {"error": f"Could not fetch movements: {str(e)}"})


# ---------------------------------------------------------------------------
# Route handlers — Suppliers (protected)
# ---------------------------------------------------------------------------
def handle_get_suppliers():
    """GET /suppliers — list all suppliers."""
    try:
        result = table.scan(FilterExpression=Attr("entityType").eq("supplier"))
        return respond(200, {"suppliers": result.get("Items", [])})
    except Exception as e:
        return respond(500, {"error": f"Could not fetch suppliers: {str(e)}"})


def handle_create_supplier(body):
    """POST /suppliers — create a new supplier."""
    name = body.get("name")
    if not name:
        return respond(400, {"error": "name is required"})

    supplier_id = str(uuid.uuid4())
    item = {
        "id": supplier_id,
        "entityType": "supplier",
        "name": name,
        "email": body.get("email", ""),
        "phone": body.get("phone", ""),
        "address": body.get("address", ""),
        "createdAt": str(int(time.time())),
        "updatedAt": str(int(time.time())),
    }

    try:
        table.put_item(Item=convert_to_decimal(item))
    except Exception as e:
        return respond(500, {"error": f"Could not create supplier: {str(e)}"})

    return respond(201, {"message": "Supplier created", "supplier": item})


def handle_update_supplier(supplier_id, body):
    """PUT /suppliers/{id} — update supplier fields."""
    try:
        result = table.get_item(Key={"id": supplier_id})
    except Exception as e:
        return respond(500, {"error": f"Database error: {str(e)}"})

    item = result.get("Item")
    if not item or item.get("entityType") != "supplier":
        return respond(404, {"error": "Supplier not found"})

    allowed = ["name", "email", "phone", "address"]
    update_expr_parts = []
    expr_values = {}
    expr_names = {}

    for field in allowed:
        if field in body:
            placeholder = f":val_{field}"
            name_placeholder = f"#field_{field}"
            update_expr_parts.append(f"{name_placeholder} = {placeholder}")
            expr_values[placeholder] = body[field]
            expr_names[name_placeholder] = field

    if not update_expr_parts:
        return respond(400, {"error": "No valid fields to update"})

    update_expr_parts.append("#updatedAt = :updatedAt")
    expr_values[":updatedAt"] = str(int(time.time()))
    expr_names["#updatedAt"] = "updatedAt"

    try:
        table.update_item(
            Key={"id": supplier_id},
            UpdateExpression="SET " + ", ".join(update_expr_parts),
            ExpressionAttributeValues=convert_to_decimal(expr_values),
            ExpressionAttributeNames=expr_names,
        )
    except Exception as e:
        return respond(500, {"error": f"Could not update supplier: {str(e)}"})

    return respond(200, {"message": "Supplier updated"})


def handle_delete_supplier(supplier_id):
    """DELETE /suppliers/{id} — delete a supplier."""
    try:
        result = table.get_item(Key={"id": supplier_id})
        item = result.get("Item")
        if not item or item.get("entityType") != "supplier":
            return respond(404, {"error": "Supplier not found"})
        table.delete_item(Key={"id": supplier_id})
    except Exception as e:
        return respond(500, {"error": f"Could not delete supplier: {str(e)}"})

    return respond(200, {"message": "Supplier deleted"})


# ---------------------------------------------------------------------------
# Route handlers — Dashboard (protected)
# ---------------------------------------------------------------------------
def handle_dashboard():
    """GET /dashboard — aggregate stats for the dashboard."""
    try:
        products_result = table.scan(FilterExpression=Attr("entityType").eq("product"))
        products = products_result.get("Items", [])

        movements_result = table.scan(FilterExpression=Attr("entityType").eq("stockMovement"))
        movements = movements_result.get("Items", [])
    except Exception as e:
        return respond(500, {"error": f"Could not fetch dashboard data: {str(e)}"})

    total_products = len(products)
    total_value = sum(
        float(p.get("price", 0)) * float(p.get("currentStock", 0)) for p in products
    )
    low_stock_count = sum(
        1 for p in products if float(p.get("currentStock", 0)) < float(p.get("minStock", 0))
    )

    # Category counts
    category_counts = {}
    for p in products:
        cat = p.get("category", "Uncategorized")
        category_counts[cat] = category_counts.get(cat, 0) + 1

    # Recent movements (last 10)
    sorted_movements = sorted(movements, key=lambda x: x.get("createdAt", ""), reverse=True)
    recent_movements = sorted_movements[:10]

    return respond(200, {
        "totalProducts": total_products,
        "totalValue": round(total_value, 2),
        "lowStockCount": low_stock_count,
        "recentMovements": recent_movements,
        "categoryCounts": category_counts,
    })


# ---------------------------------------------------------------------------
# Route handlers — Notifications (public)
# ---------------------------------------------------------------------------
def handle_subscribe(body):
    """POST /subscribe — subscribe an email to the SNS topic."""
    email = body.get("email")
    if not email:
        return respond(400, {"error": "email is required"})

    if not SNS_TOPIC_ARN:
        return respond(500, {"error": "SNS topic not configured"})

    try:
        sns_client.subscribe(
            TopicArn=SNS_TOPIC_ARN,
            Protocol="email",
            Endpoint=email,
        )
    except Exception as e:
        return respond(500, {"error": f"Could not subscribe: {str(e)}"})

    return respond(200, {"message": f"Confirmation email sent to {email}"})


def handle_get_subscribers():
    """GET /subscribers — return subscriber count."""
    if not SNS_TOPIC_ARN:
        return respond(200, {"count": 0})

    try:
        attrs = sns_client.get_topic_attributes(TopicArn=SNS_TOPIC_ARN)
        count = int(attrs["Attributes"].get("SubscriptionsConfirmed", 0))
        return respond(200, {"count": count})
    except Exception as e:
        return respond(500, {"error": f"Could not get subscribers: {str(e)}"})


# ---------------------------------------------------------------------------
# Route handler — Seed demo data (public)
# ---------------------------------------------------------------------------
def handle_seed():
    """POST /seed — populate demo user, suppliers, products, and stock movements."""
    now = str(int(time.time()))

    # --- Check if demo user already exists ---
    demo_email = "demo@smartinventory.com"
    try:
        existing = table.scan(
            FilterExpression=Attr("entityType").eq("user") & Attr("email").eq(demo_email)
        )
        if existing.get("Items"):
            return respond(200, {"message": "Demo data already exists. Login with demo@smartinventory.com / Demo1234!"})
    except Exception:
        pass

    # --- Create demo user ---
    hashed, salt = hash_password("Demo1234!")
    demo_user_id = str(uuid.uuid4())
    table.put_item(Item=convert_to_decimal({
        "id": demo_user_id, "entityType": "user",
        "username": "Demo User", "email": demo_email,
        "password": hashed, "salt": salt, "createdAt": now,
    }))

    # --- Create suppliers ---
    suppliers = [
        {"name": "TechWorld Distributors", "email": "sales@techworld.com", "phone": "+353 1 234 5678", "address": "12 Silicon Quay, Dublin 2, Ireland"},
        {"name": "Global Office Supplies", "email": "orders@globaloffice.ie", "phone": "+353 1 987 6543", "address": "Unit 5, Parkwest Business Park, Dublin 12"},
        {"name": "FreshFoods Wholesale", "email": "supply@freshfoods.ie", "phone": "+353 1 555 0199", "address": "45 Market St, Cork, Ireland"},
        {"name": "HomeStyle Furniture Co.", "email": "info@homestyle.ie", "phone": "+353 61 456 789", "address": "8 Shannon Industrial Estate, Limerick"},
        {"name": "BuildRight Tools Ltd.", "email": "trade@buildright.ie", "phone": "+353 91 321 654", "address": "Galway Retail Park, Galway"},
    ]
    supplier_ids = []
    for s in suppliers:
        sid = str(uuid.uuid4())
        supplier_ids.append(sid)
        table.put_item(Item=convert_to_decimal({
            "id": sid, "entityType": "supplier",
            "name": s["name"], "email": s["email"],
            "phone": s["phone"], "address": s["address"],
            "createdAt": now, "updatedAt": now,
        }))

    # --- Create products ---
    products = [
        {"name": "Wireless Bluetooth Mouse", "sku": "ELE-WBM-001", "category": "electronics", "price": 24.99, "currentStock": 85, "minStock": 20, "maxStock": 200, "supplier": "TechWorld Distributors", "description": "Ergonomic wireless mouse with USB receiver"},
        {"name": "USB-C Hub 7-in-1", "sku": "ELE-HUB-002", "category": "electronics", "price": 49.99, "currentStock": 42, "minStock": 15, "maxStock": 100, "supplier": "TechWorld Distributors", "description": "Multi-port adapter with HDMI, USB-A, SD card slots"},
        {"name": "Mechanical Keyboard", "sku": "ELE-MKB-003", "category": "electronics", "price": 89.99, "currentStock": 12, "minStock": 15, "maxStock": 80, "supplier": "TechWorld Distributors", "description": "RGB backlit mechanical keyboard with brown switches"},
        {"name": "27-inch Monitor Stand", "sku": "FUR-MST-001", "category": "furniture", "price": 34.99, "currentStock": 58, "minStock": 10, "maxStock": 120, "supplier": "HomeStyle Furniture Co.", "description": "Adjustable monitor riser with storage drawer"},
        {"name": "Ergonomic Office Chair", "sku": "FUR-EOC-002", "category": "furniture", "price": 249.99, "currentStock": 7, "minStock": 10, "maxStock": 50, "supplier": "HomeStyle Furniture Co.", "description": "Mesh back office chair with lumbar support"},
        {"name": "A4 Copy Paper (5 Reams)", "sku": "OFF-CPR-001", "category": "office", "price": 22.50, "currentStock": 150, "minStock": 50, "maxStock": 500, "supplier": "Global Office Supplies", "description": "80gsm white multipurpose paper, 500 sheets per ream"},
        {"name": "Whiteboard Markers (12 pk)", "sku": "OFF-WBM-002", "category": "office", "price": 8.99, "currentStock": 95, "minStock": 30, "maxStock": 200, "supplier": "Global Office Supplies", "description": "Assorted colours dry erase markers"},
        {"name": "Cordless Power Drill", "sku": "TLS-CPD-001", "category": "tools", "price": 79.99, "currentStock": 23, "minStock": 10, "maxStock": 60, "supplier": "BuildRight Tools Ltd.", "description": "18V lithium-ion drill with 2 batteries"},
        {"name": "Safety Goggles (10 pk)", "sku": "TLS-SGG-002", "category": "tools", "price": 18.50, "currentStock": 5, "minStock": 15, "maxStock": 100, "supplier": "BuildRight Tools Ltd.", "description": "Anti-fog impact-resistant safety eyewear"},
        {"name": "Organic Green Tea (50 bags)", "sku": "FOD-OGT-001", "category": "food", "price": 6.99, "currentStock": 200, "minStock": 40, "maxStock": 300, "supplier": "FreshFoods Wholesale", "description": "Certified organic green tea sachets"},
        {"name": "Instant Coffee Jar 200g", "sku": "FOD-ICJ-002", "category": "food", "price": 5.49, "currentStock": 110, "minStock": 25, "maxStock": 250, "supplier": "FreshFoods Wholesale", "description": "Premium freeze-dried instant coffee"},
        {"name": "Cotton Polo Shirt (L)", "sku": "CLO-CPS-001", "category": "clothing", "price": 19.99, "currentStock": 65, "minStock": 20, "maxStock": 150, "supplier": "Global Office Supplies", "description": "Company branded navy cotton polo"},
        {"name": "Hi-Vis Safety Vest", "sku": "CLO-HVS-002", "category": "clothing", "price": 12.50, "currentStock": 3, "minStock": 20, "maxStock": 100, "supplier": "BuildRight Tools Ltd.", "description": "EN ISO 20471 Class 2 fluorescent yellow vest"},
        {"name": "Standing Desk Converter", "sku": "FUR-SDC-003", "category": "furniture", "price": 179.99, "currentStock": 18, "minStock": 5, "maxStock": 40, "supplier": "HomeStyle Furniture Co.", "description": "Height adjustable sit-stand desktop workstation"},
        {"name": "Label Printer", "sku": "OFF-LBP-003", "category": "office", "price": 64.99, "currentStock": 14, "minStock": 5, "maxStock": 30, "supplier": "TechWorld Distributors", "description": "Thermal label printer for shipping and barcodes"},
    ]
    product_ids = []
    for p in products:
        pid = str(uuid.uuid4())
        product_ids.append(pid)
        table.put_item(Item=convert_to_decimal({
            "id": pid, "entityType": "product",
            "name": p["name"], "sku": p["sku"], "category": p["category"],
            "description": p["description"], "price": p["price"],
            "minStock": p["minStock"], "maxStock": p["maxStock"],
            "currentStock": p["currentStock"], "supplier": p["supplier"],
            "createdAt": now, "updatedAt": now,
        }))

    # --- Create stock movements (realistic history) ---
    movements = [
        {"idx": 0, "type": "intake", "qty": 100, "prev": 0, "new": 100, "ref": "PO-2026-001", "notes": "Initial stock from TechWorld"},
        {"idx": 0, "type": "dispatch", "qty": 15, "prev": 100, "new": 85, "ref": "SO-2026-044", "notes": "Shipped to warehouse B"},
        {"idx": 1, "type": "intake", "qty": 50, "prev": 0, "new": 50, "ref": "PO-2026-003", "notes": "New shipment received"},
        {"idx": 1, "type": "dispatch", "qty": 8, "prev": 50, "new": 42, "ref": "SO-2026-051", "notes": "Office setup order"},
        {"idx": 2, "type": "intake", "qty": 30, "prev": 0, "new": 30, "ref": "PO-2026-005", "notes": "Keyboard restock"},
        {"idx": 2, "type": "dispatch", "qty": 18, "prev": 30, "new": 12, "ref": "SO-2026-062", "notes": "Bulk order - IT dept"},
        {"idx": 4, "type": "intake", "qty": 20, "prev": 0, "new": 20, "ref": "PO-2026-010", "notes": "Chair delivery"},
        {"idx": 4, "type": "dispatch", "qty": 13, "prev": 20, "new": 7, "ref": "SO-2026-071", "notes": "New hires setup"},
        {"idx": 5, "type": "intake", "qty": 200, "prev": 0, "new": 200, "ref": "PO-2026-012", "notes": "Monthly paper order"},
        {"idx": 5, "type": "dispatch", "qty": 50, "prev": 200, "new": 150, "ref": "SO-2026-078", "notes": "Floor 3 restock"},
        {"idx": 8, "type": "intake", "qty": 25, "prev": 0, "new": 25, "ref": "PO-2026-018", "notes": "Safety gear order"},
        {"idx": 8, "type": "dispatch", "qty": 20, "prev": 25, "new": 5, "ref": "SO-2026-085", "notes": "Site safety kits"},
        {"idx": 12, "type": "intake", "qty": 15, "prev": 0, "new": 15, "ref": "PO-2026-022", "notes": "PPE restock"},
        {"idx": 12, "type": "dispatch", "qty": 12, "prev": 15, "new": 3, "ref": "SO-2026-090", "notes": "Construction site delivery"},
    ]
    base_ts = int(now) - 86400 * 14  # 14 days ago start
    for i, m in enumerate(movements):
        mid = str(uuid.uuid4())
        table.put_item(Item=convert_to_decimal({
            "id": mid, "entityType": "stockMovement",
            "productId": product_ids[m["idx"]],
            "productName": products[m["idx"]]["name"],
            "type": m["type"], "quantity": m["qty"],
            "previousStock": m["prev"], "newStock": m["new"],
            "reference": m["ref"], "notes": m["notes"],
            "createdAt": str(base_ts + i * 3600 * 8),
        }))

    return respond(201, {
        "message": "Demo data seeded successfully",
        "summary": {
            "user": demo_email,
            "password": "Demo1234!",
            "suppliers": len(suppliers),
            "products": len(products),
            "stockMovements": len(movements),
        }
    })


# ---------------------------------------------------------------------------
# Main Lambda handler
# ---------------------------------------------------------------------------
def lambda_handler(event, context):
    """Route incoming API Gateway requests to the correct handler."""
    http_method = event.get("httpMethod", "GET")
    path = event.get("path", "/")
    headers = event.get("headers") or {}
    body = {}

    # Parse body
    if event.get("body"):
        try:
            body = json.loads(event["body"])
        except (json.JSONDecodeError, TypeError):
            body = {}

    # Handle OPTIONS preflight FIRST
    if http_method == "OPTIONS":
        return respond(200, {"message": "OK"})

    # -----------------------------------------------------------------------
    # Public routes (NO auth required) — must be checked BEFORE auth
    # -----------------------------------------------------------------------
    if path == "/subscribe" and http_method == "POST":
        return handle_subscribe(body)

    if path == "/subscribers" and http_method == "GET":
        return handle_get_subscribers()

    # -----------------------------------------------------------------------
    # Auth routes (no token needed)
    # -----------------------------------------------------------------------
    if path == "/auth/register" and http_method == "POST":
        return handle_register(body)

    if path == "/auth/login" and http_method == "POST":
        return handle_login(body)

    if path == "/seed" and http_method == "POST":
        return handle_seed()

    # -----------------------------------------------------------------------
    # Protected routes — verify token
    # -----------------------------------------------------------------------
    user = extract_user(headers)
    if not user:
        return respond(401, {"error": "Unauthorized. Please provide a valid token."})

    # --- Products ---
    if path == "/products" and http_method == "GET":
        return handle_get_products()

    if path == "/products" and http_method == "POST":
        return handle_create_product(body)

    # /products/{id}/stock
    if "/products/" in path and path.endswith("/stock"):
        product_id = path.split("/")[2]
        if http_method == "POST":
            return handle_create_stock_movement(product_id, body)
        if http_method == "GET":
            return handle_get_stock_movements(product_id)

    # /products/{id}
    if path.startswith("/products/") and path.count("/") == 2:
        product_id = path.split("/")[2]
        if http_method == "GET":
            return handle_get_product(product_id)
        if http_method == "PUT":
            return handle_update_product(product_id, body)
        if http_method == "DELETE":
            return handle_delete_product(product_id)

    # --- Suppliers ---
    if path == "/suppliers" and http_method == "GET":
        return handle_get_suppliers()

    if path == "/suppliers" and http_method == "POST":
        return handle_create_supplier(body)

    if path.startswith("/suppliers/") and path.count("/") == 2:
        supplier_id = path.split("/")[2]
        if http_method == "PUT":
            return handle_update_supplier(supplier_id, body)
        if http_method == "DELETE":
            return handle_delete_supplier(supplier_id)

    # --- Dashboard ---
    if path == "/dashboard" and http_method == "GET":
        return handle_dashboard()

    # -----------------------------------------------------------------------
    # Fallback
    # -----------------------------------------------------------------------
    return respond(404, {"error": f"Route not found: {http_method} {path}"})
