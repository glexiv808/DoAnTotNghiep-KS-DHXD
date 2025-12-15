"""
Script test endpoint /evaluate
"""
import requests
import json
import pandas as pd

API_BASE_URL = "http://127.0.0.1:5000"

# 1. Register user
print("1. Đăng ký tài khoản test...")
register_data = {
    "username": "testuser",
    "email": "test@example.com",
    "password": "password123",
    "full_name": "Test User"
}

try:
    response = requests.post(f"{API_BASE_URL}/register", json=register_data)
    print(f"Register response: {response.status_code}")
    if response.status_code == 200:
        print("✓ Đăng ký thành công")
    else:
        print(f"Register error: {response.text}")
except Exception as e:
    print(f"Register error: {e}")

# 2. Login
print("\n2. Đăng nhập...")
login_data = {
    "username": "testuser",
    "password": "password123"
}

token = None
try:
    response = requests.post(f"{API_BASE_URL}/login", json=login_data)
    print(f"Login response: {response.status_code}")
    if response.status_code == 200:
        token = response.json().get("access_token")
        print(f"✓ Đăng nhập thành công, token: {token[:20]}...")
    else:
        print(f"Login error: {response.text}")
except Exception as e:
    print(f"Login error: {e}")

# 3. Load test data
print("\n3. Tạo dữ liệu test...")
test_df = pd.read_csv("jupiter_notebook/loan_data.csv")
test_data = test_df.head(100).to_dict('records')
print(f"✓ Tạo {len(test_data)} bản ghi test")

# 4. Call /evaluate endpoint
print("\n4. Gọi endpoint /evaluate...")
headers = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {token}" if token else ""
}

try:
    response = requests.post(
        f"{API_BASE_URL}/evaluate",
        json=test_data,
        headers=headers,
        timeout=60
    )
    print(f"Evaluate response: {response.status_code}")
    
    if response.status_code == 200:
        result = response.json()
        print("✓ Gọi thành công!")
        print("\n=== KẾT QUẢ SO SÁNH 3 MÔ HÌNH ===\n")
        
        # XGBoost
        xgb = result.get('xgboost', {})
        print(f"XGBoost:")
        print(f"  - Accuracy:  {xgb.get('accuracy', 0):.4f}")
        print(f"  - Precision: {xgb.get('precision', 0):.4f}")
        print(f"  - Recall:    {xgb.get('recall', 0):.4f}")
        print(f"  - F1-Score:  {xgb.get('f1', 0):.4f}")
        print(f"  - Time:      {xgb.get('time', 0):.2f}ms")
        
        # Random Forest
        rf = result.get('random_forest', {})
        print(f"\nRandom Forest:")
        print(f"  - Accuracy:  {rf.get('accuracy', 0):.4f}")
        print(f"  - Precision: {rf.get('precision', 0):.4f}")
        print(f"  - Recall:    {rf.get('recall', 0):.4f}")
        print(f"  - F1-Score:  {rf.get('f1', 0):.4f}")
        print(f"  - Time:      {rf.get('time', 0):.2f}ms")
        
        # Logistic Regression
        lr = result.get('logistic_regression', {})
        print(f"\nLogistic Regression:")
        print(f"  - Accuracy:  {lr.get('accuracy', 0):.4f}")
        print(f"  - Precision: {lr.get('precision', 0):.4f}")
        print(f"  - Recall:    {lr.get('recall', 0):.4f}")
        print(f"  - F1-Score:  {lr.get('f1', 0):.4f}")
        print(f"  - Time:      {lr.get('time', 0):.2f}ms")
        
        # Tìm mô hình tốt nhất
        print("\n=== TỔNG QUÁT ===")
        accuracies = {
            'XGBoost': xgb.get('accuracy', 0),
            'Random Forest': rf.get('accuracy', 0),
            'Logistic Regression': lr.get('accuracy', 0)
        }
        best_model = max(accuracies, key=accuracies.get)
        print(f"✓ Mô hình tốt nhất: {best_model} (Accuracy: {accuracies[best_model]:.4f})")
        
    else:
        print(f"Evaluate error: {response.text}")
except Exception as e:
    print(f"Evaluate error: {e}")

print("\n✓ Test hoàn tất!")
