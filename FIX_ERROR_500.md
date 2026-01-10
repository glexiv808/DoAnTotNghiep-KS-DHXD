# 🔴 FIX Lỗi 500 - Register & Prediction API

## 📍 Nguyên Nhân Lỗi 500

Lỗi 500 thường do:
1. ❌ Database không kết nối được
2. ❌ Models joblib không load được
3. ❌ Dữ liệu request không đúng format
4. ❌ Environment variables không set
5. ❌ Dependency missing

---

## 🔍 Debug Step 1: Kiểm Tra Logs Backend

```bash
# Xem logs backend
kubectl logs -f deployment/ml-backend --tail=100

# Hoặc để tất cả containers
kubectl logs -f deployment/ml-backend --all-containers=true

# Hoặc xem log của pod cụ thể
kubectl logs -f <POD_NAME> -c ml-backend
```

**Tìm kiếm**: `ERROR`, `Traceback`, `Exception`

---

## 🔍 Debug Step 2: Kiểm Tra Pod Status

```bash
# Xem chi tiết pod
kubectl describe pod <POD_NAME>

# Xem events
kubectl get events --sort-by='.lastTimestamp'

# Xem resource usage
kubectl top pods
```

---

## 🔧 Fix #1: Database Connection Error

### Triệu Chứng
```
ERROR: (psycopg2.OperationalError) could not connect to server
ERROR: sqlite3.OperationalError: database is locked
```

### Cách Fix

**Option A: Dùng SQLite (nhanh nhất)**
```bash
# Sửa k8s-secrets.yaml
kubectl edit secret ml-secrets

# Thay DATABASE_URL thành:
database-url: "sqlite:///./ml_service.db"

# Restart pod
kubectl rollout restart deployment/ml-backend
```

**Option B: Dùng PostgreSQL**
```bash
# Tạo PostgreSQL instance (nếu chưa có)
# Hoặc dùng GCP CloudSQL

# Update k8s-secrets.yaml
database-url: "postgresql://username:password@postgresql:5432/ml_db"

# Restart pod
kubectl rollout restart deployment/ml-backend
```

---

## 🔧 Fix #2: Models Not Loading

### Triệu Chứng
```
ERROR: FileNotFoundError: [Errno 2] No such file or directory: 'model_ml.joblib'
```

### Cách Fix

**Kiểm tra xem models có trong pod không:**
```bash
kubectl exec -it <POD_NAME> -- ls -la /app/model_*.joblib
```

**Nếu không có:**
1. Kiểm tra Dockerfile:
```dockerfile
COPY jupiter_notebook/model_ml.joblib /app/
COPY jupiter_notebook/model_logistic_regression.joblib /app/
COPY jupiter_notebook/model_random_forest.joblib /app/
COPY jupiter_notebook/model_xgboost.joblib /app/
COPY jupiter_notebook/scaler_logistic_regression.joblib /app/
```

2. Rebuild & push image:
```bash
docker build -t gcr.io/YOUR_PROJECT_ID/ml-backend:latest .
docker push gcr.io/YOUR_PROJECT_ID/ml-backend:latest
```

3. Redeploy:
```bash
kubectl rollout restart deployment/ml-backend
```

---

## 🔧 Fix #3: Request Format Error

### Triệu Chứng
```
ERROR: Validation error: 'income' field required
ERROR: pydantic.validation.ValidationError
```

### Register API - Format Đúng
```json
{
  "username": "testuser",
  "email": "test@example.com",
  "password": "Str0ng@Pass123",
  "full_name": "Test User"
}
```

### Predict API - Format Đúng
```json
{
  "income": 5000000,
  "score": 750,
  "contact_status": "contacted"
}
```

### Test bằng curl:
```bash
# Register
curl -X POST http://34.87.54.108.nip.io/register \
  -H "Content-Type: application/json" \
  -d '{
    "username": "testuser",
    "email": "test@test.com",
    "password": "Test@123456",
    "full_name": "Test User"
  }'

# Predict
curl -X POST http://34.87.54.108.nip.io/predict \
  -H "Content-Type: application/json" \
  -d '{
    "income": 5000000,
    "score": 750,
    "contact_status": "contacted"
  }'
```

---

## 🔧 Fix #4: Environment Variables Not Set

### Kiểm Tra Env Variables:
```bash
kubectl exec -it <POD_NAME> -- env | grep -E "DATABASE_URL|SECRET_KEY"
```

### Nếu không có:
```bash
# Check secret
kubectl get secret ml-secrets -o yaml

# Verify secret mounted
kubectl describe pod <POD_NAME> | grep -A 10 "Environment:"
```

### Sửa k8s-backend-deployment.yaml:
```yaml
env:
- name: DATABASE_URL
  valueFrom:
    secretKeyRef:
      name: ml-secrets
      key: database-url
- name: SECRET_KEY
  valueFrom:
    secretKeyRef:
      name: ml-secrets
      key: secret-key
```

---

## 🔧 Fix #5: Missing Dependencies

### Triệu Chứng
```
ERROR: ModuleNotFoundError: No module named 'numpy'
ERROR: ModuleNotFoundError: No module named 'sklearn'
```

### Cách Fix

1. Kiểm tra requirements.txt:
```bash
pip install -r requirements.txt
```

2. Verify package:
```bash
docker run <IMAGE_ID> pip list | grep -E "numpy|sklearn|joblib"
```

3. Rebuild image:
```bash
docker build --no-cache -t gcr.io/YOUR_PROJECT_ID/ml-backend:latest .
docker push gcr.io/YOUR_PROJECT_ID/ml-backend:latest
kubectl rollout restart deployment/ml-backend
```

---

## 📊 Complete Debug Workflow

### 1. Kiểm Tra Pod Status
```bash
kubectl get pods -l app=ml-backend
```
**Expected**: `1/1 Ready`

### 2. Xem Logs
```bash
kubectl logs -f deployment/ml-backend --tail=50
```
**Tìm kiếm error messages**

### 3. Describe Pod
```bash
kubectl describe pod <POD_NAME>
```
**Kiểm tra**: Events, Mounts, Environment

### 4. Test API Directly
```bash
# Port forward
kubectl port-forward svc/ml-backend 5000:80

# Test trong tab khác
curl http://localhost:5000/health
curl http://localhost:5000/docs
```

### 5. Exec vào Pod
```bash
kubectl exec -it <POD_NAME> -- /bin/bash

# Sau đó chạy trong container:
python -c "import joblib; model = joblib.load('/app/model_ml.joblib')"
python -c "from sqlalchemy import create_engine; engine = create_engine('sqlite:///./ml_service.db'); print('DB OK')"
```

---

## 🧪 Test API Script

```python
import requests
import json

BASE_URL = "http://34.87.54.108.nip.io"

# Test 1: Health Check
print("1. Testing Health...")
r = requests.get(f"{BASE_URL}/health")
print(f"Status: {r.status_code}")
print(f"Response: {r.json()}\n")

# Test 2: Register
print("2. Testing Register...")
r = requests.post(f"{BASE_URL}/register", json={
    "username": "testuser",
    "email": "test@test.com",
    "password": "Test@123456",
    "full_name": "Test User"
})
print(f"Status: {r.status_code}")
print(f"Response: {r.json()}\n")

# Test 3: Login
print("3. Testing Login...")
r = requests.post(f"{BASE_URL}/login", data={
    "username": "testuser",
    "password": "Test@123456"
})
print(f"Status: {r.status_code}")
token = r.json().get("access_token")
print(f"Token: {token[:20]}...\n")

# Test 4: Predict
print("4. Testing Predict...")
r = requests.post(f"{BASE_URL}/predict", 
    json={
        "income": 5000000,
        "score": 750,
        "contact_status": "contacted"
    },
    headers={"Authorization": f"Bearer {token}"}
)
print(f"Status: {r.status_code}")
print(f"Response: {r.json()}\n")
```

---

## 📋 Checklist Khi Gặp Lỗi 500

- [ ] Kiểm tra backend logs: `kubectl logs -f deployment/ml-backend`
- [ ] Kiểm tra pod status: `kubectl get pods`
- [ ] Kiểm tra database connection
- [ ] Kiểm tra models được load: `ls /app/model_*.joblib`
- [ ] Kiểm tra environment variables
- [ ] Test API locally với port-forward
- [ ] Verify request format đúng
- [ ] Rebuild & redeploy nếu cần

---

## 🆘 Nếu Still không fix được

1. **Collect logs:**
```bash
kubectl logs deployment/ml-backend > backend_logs.txt
kubectl describe deployment ml-backend > deployment_info.txt
kubectl get events > events.txt
```

2. **Check image:**
```bash
docker history gcr.io/YOUR_PROJECT_ID/ml-backend:latest
docker inspect gcr.io/YOUR_PROJECT_ID/ml-backend:latest
```

3. **Rebuild from scratch:**
```bash
docker build --no-cache -t gcr.io/YOUR_PROJECT_ID/ml-backend:v2 .
docker push gcr.io/YOUR_PROJECT_ID/ml-backend:v2
# Edit k8s-backend-deployment.yaml image tag
kubectl apply -f k8s-backend-deployment.yaml
```

---

**Tips**: Luôn kiểm tra logs trước, 99% lỗi sẽ báo ở logs! 📝
