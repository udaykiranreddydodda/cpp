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
SQS_QUEUE_URL = os.environ.get("SQS_QUEUE_URL", "")
REGION = os.environ.get("REGION", "eu-west-1")
JWT_SECRET = os.environ.get("JWT_SECRET", "smartinventory-secret-2026")

# AWS clients
dynamodb = boto3.resource("dynamodb", region_name=REGION)
table = dynamodb.Table(TABLE_NAME)
sqs_client = boto3.client("sqs", region_name=REGION)
cloudwatch_client = boto3.client("cloudwatch", region_name=REGION)

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
# Helpers — SQS + CloudWatch
# ---------------------------------------------------------------------------
def send_sqs_message(action, entity_type, details):
    """Send a message to SQS queue about a CRUD operation (non-critical)."""
    if not SQS_QUEUE_URL:
        return
    try:
        sqs_client.send_message(
            QueueUrl=SQS_QUEUE_URL,
            MessageBody=json.dumps({
                "action": action,
                "entityType": entity_type,
                "details": details,
                "timestamp": str(int(time.time())),
            }, default=str),
        )
    except Exception:
        pass  # Non-critical — don't fail the request


def push_cloudwatch_metrics():
    """Push custom inventory metrics to CloudWatch (non-critical)."""
    try:
        result = table.scan(FilterExpression=Attr("entityType").eq("product"))
        products = result.get("Items", [])
        total_products = len(products)
        low_stock_count = sum(
            1 for p in products
            if float(p.get("currentStock", 0)) < float(p.get("minStock", 0))
        )
        cloudwatch_client.put_metric_data(
            Namespace="SmartInventory",
            MetricData=[
                {
                    "MetricName": "TotalProducts",
                    "Value": total_products,
                    "Unit": "Count",
                },
                {
                    "MetricName": "LowStockItems",
                    "Value": low_stock_count,
                    "Unit": "Count",
                },
            ],
        )
    except Exception:
        pass  # Non-critical — don't fail the request


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

    send_sqs_message("CREATE", "product", {"id": product_id, "name": body.get("name"), "sku": body.get("sku")})
    push_cloudwatch_metrics()
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

    send_sqs_message("UPDATE", "product", {"id": product_id, "fields": list(body.keys())})
    push_cloudwatch_metrics()
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

    send_sqs_message("DELETE", "product", {"id": product_id})
    push_cloudwatch_metrics()
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

    # Send SQS message for stock movement and push CloudWatch metrics
    send_sqs_message("STOCK_MOVEMENT", "product", {
        "id": product_id,
        "name": product.get("name"),
        "type": movement_type,
        "quantity": quantity,
        "newStock": new_stock,
    })
    push_cloudwatch_metrics()

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
# Route handlers — Queue Status (public)
# ---------------------------------------------------------------------------
def handle_queue_status():
    """GET /queue-status — return SQS queue attributes."""
    if not SQS_QUEUE_URL:
        return respond(200, {"messages": 0, "configured": False})

    try:
        attrs = sqs_client.get_queue_attributes(
            QueueUrl=SQS_QUEUE_URL,
            AttributeNames=["ApproximateNumberOfMessages"],
        )
        count = int(attrs["Attributes"].get("ApproximateNumberOfMessages", 0))
        return respond(200, {"messages": count, "configured": True})
    except Exception as e:
        return respond(500, {"error": f"Could not get queue status: {str(e)}"})


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
    if path == "/queue-status" and http_method == "GET":
        return handle_queue_status()

    # -----------------------------------------------------------------------
    # Auth routes (no token needed)
    # -----------------------------------------------------------------------
    if path == "/auth/register" and http_method == "POST":
        return handle_register(body)

    if path == "/auth/login" and http_method == "POST":
        return handle_login(body)

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
