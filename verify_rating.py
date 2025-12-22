import sys
import os

# Set environment variable BEFORE importing app to ensure it picks up the admin ID
os.environ["ADMIN_TELEGRAM_IDS"] = "123456789"

# Add the parent directory to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient
from app.main import app
import time

client = TestClient(app)

def test_rating_flow():
    # 1. Create Admin (Mocking authentication via header X-Telegram-ID for simplicity as per bot logic)
    # The current logic uses X-Telegram-ID header for admin checks in some routers, 
    # but the `require_admin` dependency might check env vars.
    # Let's check `dependencies.py` or just try to rely on the fact that ADMIN_TELEGRAM_IDS is used.
    # In `bot_admin.py` it uses `ADMIN_TELEGRAM_IDS` from env.
    
    # We will simulate headers.
    admin_id = "123456789"
    # os.environ["ADMIN_TELEGRAM_IDS"] = admin_id # Already set at top
    
    # 2. Create User
    user_payload = {
        "telegram_id": "987654321",
        "name": "Test User",
        "phone": "+998901234567",
        "address": "Test Address"
    }
    res = client.post("/users/", json=user_payload)
    print(f"User Create: {res.status_code}")
    assert res.status_code in [200, 201]
    user_id = res.json()["id"]

    # 3. Create Courier
    courier_payload = {
        "name": "Test Courier",
        "phone": "+998991234567",
        "telegram_id": "111222333",
        "tg_username": "testcourier"
    }
    # Create courier requires admin
    # The `require_admin` dependency usually checks if the caller is in the admin list.
    # Let's check `app/dependencies.py` quickly.
    # But for now, let's assume valid admin header if we pass `X-Telegram-ID`.
    
    # Actually, let's skip auth complexity if possible or mock it.
    # Assuming `require_admin` checks `X-Telegram-ID` header against `ADMIN_TELEGRAM_IDS`.
    
    headers = {"X-Telegram-ID": admin_id}
    res = client.post("/couriers/", json=courier_payload, headers=headers)
    print(f"Courier Create: {res.status_code}")
    if res.status_code != 201:
        print(res.json())
    assert res.status_code == 201
    courier_id = res.json()["id"]

    # 4. Create Product
    # The endpoint expects Form data and File
    # We also need to mock cloudinary upload to avoid external calls
    
    # Mock cloudinary
    from unittest.mock import patch
    with patch("app.routers.products.upload_to_cloudinary") as mock_upload:
        mock_upload.return_value = {"url": "http://mock-url.com/image.jpg", "public_id": "mock_id"}
        
        product_data = {
            "name": "Test Product",
            "buy_price": "10000",
            "sell_price": "15000",
            "stock": "100"
        }
        files = {
            "image": ("test.jpg", b"fake_image_content", "image/jpeg")
        }
        
        # Note: headers for auth are still needed, but Content-Type will be auto-set to multipart
        res = client.post("/products/", data=product_data, files=files, headers=headers)
        print(f"Product Create: {res.status_code}")
        if res.status_code != 200:
             print(res.json())
        # The endpoint returns the created product
        # Note: response_model is ProductDetailRead, check app/schemas/product.py if it has id
        # Usually it returns the DB model which has id.
        product_id = res.json()["id"]

    # 5. Create Order
    order_payload = {
        "telegram_id": "987654321",
        "items": [
            {"product_id": product_id, "quantity": 2}
        ]
    }
    res = client.post("/orders/", json=order_payload)
    print(f"Order Create: {res.status_code}")
    assert res.status_code == 201
    order_id = res.json()["id"]

    # 6. Assign Courier
    res = client.patch(f"/orders/{order_id}/assign", json={"courier_id": courier_id}, headers=headers)
    print(f"Order Assign: {res.status_code}")
    assert res.status_code == 200

    # 7. Accept Order
    res = client.patch(f"/orders/{order_id}/accept", json={"delivery_time": "30 min"})
    print(f"Order Accept: {res.status_code}")
    assert res.status_code == 200

    # 7.5 ADD BONUS ITEMS (NEW FEATURE)
    print("Adding Bonus Items...")
    bonus_payload = [
        {"product_id": product_id, "quantity": 1}
    ]
    res = client.post(f"/orders/{order_id}/bonus", json=bonus_payload)
    print(f"Add Bonus: {res.status_code}")
    assert res.status_code == 200
    
    order_data = res.json()
    # Check if bonus item added
    # Total items should be 2 (1 original + 1 bonus)
    # Actually wait, original was 1 item line (qty 2).
    # New bonus item is a separate line in OrderItem usually? 
    # Yes, DB add(db_item) creates new row.
    assert len(order_data["items"]) == 2
    bonus_item = next(i for i in order_data["items"] if i["is_bonus"])
    assert bonus_item["price"] == 0.0
    assert bonus_item["total"] == 0.0
    
    # Check total amount of order - should NOT change
    # Original: 2 * 15000 = 30000
    assert order_data["total_amount"] == 30000.0

    # 8. Deliver Order
    res = client.patch(f"/orders/{order_id}/deliver")
    print(f"Order Deliver: {res.status_code}")
    assert res.status_code == 200

    # 9. Rate Order (THE NEW FEATURE)
    print("Testing Rating...")
    
    # Case 1: Invalid Rating (>5)
    res = client.post(f"/orders/{order_id}/rate", json={"rating": 6, "comment": "Too high"})
    print(f"Invalid Rating Check: {res.status_code}")
    assert res.status_code == 400

    # Case 2: Valid Rating
    res = client.post(f"/orders/{order_id}/rate", json={"rating": 5, "comment": "Great service!"})
    print(f"Valid Rating Check: {res.status_code}")
    assert res.status_code == 200
    data = res.json()
    assert data["rating"] == 5
    assert data["rating_comment"] == "Great service!"

    # 10. Check Courier Stats
    print("Checking Courier Stats...")
    res = client.get(f"/couriers/{courier_id}/history", headers=headers)
    print(f"Courier Stats Check: {res.status_code}")
    assert res.status_code == 200
    stats = res.json()
    print(f"Stats: {stats}")
    
    assert stats["average_rating"] == 5.0
    assert len(stats["history"]) == 1
    assert stats["history"][0]["rating"] == 5

    print("\n✅ VERIFICATION SUCCESSFUL!")

if __name__ == "__main__":
    test_rating_flow()
