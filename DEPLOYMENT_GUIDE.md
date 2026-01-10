# Hướng Dẫn Triển Khai Frontend & Backend trên GKE

## 1. Build Images

### Build Backend Image
```bash
# Đứng ở thư mục gốc của dự án
docker build -t gcr.io/YOUR_PROJECT_ID/ml-backend:latest .
docker push gcr.io/YOUR_PROJECT_ID/ml-backend:latest
```

### Build Frontend Image
```bash
# Đứng ở thư mục gốc của dự án
docker build -t gcr.io/YOUR_PROJECT_ID/ml-frontend:latest ./UI
docker push gcr.io/YOUR_PROJECT_ID/ml-frontend:latest
```

**Thay `YOUR_PROJECT_ID` với GCP Project ID của bạn**

---

## 2. Chuẩn Bị Kubernetes Cluster

```bash
# Kiểm tra cluster context
kubectl config current-context

# Đảm bảo cluster được activate
gcloud container clusters get-credentials gke-ml-ops-02 --zone asia-southeast1-a --project YOUR_PROJECT_ID
```

---

## 3. Tạo Secrets & ConfigMap

```bash
# Tạo Secret chứa thông tin Database
kubectl apply -f k8s-secrets.yaml

# Kiểm tra Secret
kubectl get secrets ml-secrets -o yaml
```

**Chỉnh sửa `k8s-secrets.yaml` trước nếu bạn sử dụng PostgreSQL hoặc MySQL**

---

## 4. Deploy Backend

```bash
# Cập nhật image URL trong k8s-backend-deployment.yaml
kubectl apply -f k8s-backend-deployment.yaml

# Kiểm tra deployment
kubectl get deployments ml-backend
kubectl get pods -l app=ml-backend
kubectl logs -f deployment/ml-backend
```

---

## 5. Deploy Frontend

```bash
kubectl apply -f k8s-frontend-deployment.yaml

# Kiểm tra deployment
kubectl get deployments ml-frontend
kubectl get pods -l app=ml-frontend
kubectl logs -f deployment/ml-frontend
```

---

## 6. Deploy Ingress

```bash
# Cập nhật host trong k8s-ingress.yaml nếu cần
kubectl apply -f k8s-ingress.yaml

# Kiểm tra Ingress
kubectl get ingress ml-app-ingress
kubectl describe ingress ml-app-ingress
```

---

## 7. Kiểm Tra & Test

### Kiểm tra dịch vụ
```bash
# Liệt kê tất cả services
kubectl get svc

# Kiểm tra Ingress IP
kubectl get ingress
```

### Test API Backend
```bash
# Truy cập API docs
curl http://34.87.54.108.nip.io/docs

# Hoặc trên trình duyệt
http://34.87.54.108.nip.io/docs
```

### Test Frontend
```bash
# Truy cập Frontend
http://34.87.54.108.nip.io/
```

---

## 8. Xử Lý Lỗi

### Kiểm tra log Backend
```bash
kubectl logs -f deployment/ml-backend
```

### Kiểm tra log Frontend
```bash
kubectl logs -f deployment/ml-frontend
```

### Kiểm tra Pod Status
```bash
kubectl describe pod <pod-name>
```

### Port Forward để Debug
```bash
# Backend
kubectl port-forward svc/ml-backend 5000:80

# Frontend
kubectl port-forward svc/ml-frontend 8080:80
```

---

## 9. Cập Nhật Configurations

### Sửa Database URL (nếu dùng PostgreSQL/MySQL)
```bash
kubectl edit secret ml-secrets

# Hoặc
kubectl delete secret ml-secrets
# Sửa k8s-secrets.yaml rồi
kubectl apply -f k8s-secrets.yaml
```

### Scale Replicas
```bash
kubectl scale deployment ml-backend --replicas=5
kubectl scale deployment ml-frontend --replicas=3
```

---

## 10. Lỗi 500 Common Fixes

### Kiểm tra Database Connection
- Đảm bảo DATABASE_URL đúng trong k8s-secrets.yaml
- Kiểm tra log: `kubectl logs -f deployment/ml-backend`

### Kiểm tra Models Được Load
- Đảm bảo tất cả model files được COPY trong Dockerfile
- Kiểm tra path trong code: `/app/model_*.joblib`

### CORS Issues
- Frontend cần gọi API qua `/api` path
- Ingress đã có cấu hình CORS

---

## 11. Clean Up (Nếu cần)

```bash
# Xóa Deployment & Services
kubectl delete -f k8s-frontend-deployment.yaml
kubectl delete -f k8s-backend-deployment.yaml
kubectl delete -f k8s-ingress.yaml
kubectl delete -f k8s-secrets.yaml
```

---

## 12. File cần Cập Nhật

Trước khi triển khai, hãy sửa:

1. **k8s-backend-deployment.yaml**: Thay `YOUR_PROJECT_ID` bằng GCP Project ID
2. **k8s-frontend-deployment.yaml**: Thay `YOUR_PROJECT_ID` bằng GCP Project ID
3. **k8s-ingress.yaml**: Thay URL nếu cần (hiện là `34.87.54.108.nip.io`)
4. **k8s-secrets.yaml**: Cập nhật DATABASE_URL nếu dùng DB khác

---

## 13. Sơ Đồ Triển Khai

```
┌─────────────────────────────────────────────────────────────────┐
│                   Kubernetes Cluster (GKE)                      │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │              Ingress (ml-app-ingress)                      │ │
│  │  Host: 34.87.54.108.nip.io                                │ │
│  └────────────────────────────────────────────────────────────┘ │
│            ↓                                        ↓             │
│  ┌──────────────────────────┐    ┌──────────────────────────┐   │
│  │   Frontend Service       │    │   Backend Service        │   │
│  │   (ml-frontend)          │    │   (ml-backend)           │   │
│  │   Port: 80               │    │   Port: 80               │   │
│  └──────────────────────────┘    └──────────────────────────┘   │
│            ↓                                        ↓             │
│  ┌──────────────────────────┐    ┌──────────────────────────┐   │
│  │ Frontend Pods (2x)       │    │ Backend Pods (3x)        │   │
│  │ - Nginx Container        │    │ - FastAPI Container      │   │
│  │ - Static Files (UI)      │    │ - ML Models              │   │
│  └──────────────────────────┘    └──────────────────────────┘   │
│                                            ↓                      │
│                                  ┌──────────────────────┐        │
│                                  │   Database           │        │
│                                  │ (SQLite/PostgreSQL) │        │
│                                  │ (k8s-secrets)        │        │
│                                  └──────────────────────┘        │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Lưu Ý Quan Trọng

- ✅ Sửa `YOUR_PROJECT_ID` trong tất cả file YAML
- ✅ Build & Push images trước khi deploy
- ✅ Kiểm tra Secret & ConfigMap được tạo đúng
- ✅ Chờ pods chạy sạch: `kubectl get pods -w`
- ✅ Kiểm tra logs nếu có lỗi: `kubectl logs -f <pod-name>`
