# ✅ Pre-Deployment Checklist

## 📋 Chuẩn Bị Trước Khi Deploy

### 1. Cài Đặt Tools Cần Thiết
- [ ] Docker desktop cài đặt & chạy
- [ ] kubectl cài đặt
- [ ] gcloud CLI cài đặt
- [ ] Git cài đặt

### 2. Xác Nhận GCP Project
- [ ] GCP Project ID biết chắc
- [ ] GCP Project có enabled Compute Engine, Kubernetes Engine, Container Registry
- [ ] Tài khoản GCP có quyền cần thiết (Compute Admin, Kubernetes Admin)
- [ ] Quota đủ cho GKE cluster

### 3. Xác Nhận Kubernetes Cluster
- [ ] GKE Cluster `gke-ml-ops-02` đã tồn tại
- [ ] Zone: `asia-southeast1-a` (chính xác?)
- [ ] Cluster có ít nhất 3 nodes (hoặc 1 node, có thể scale up sau)
- [ ] Node pool có đủ resource (CPU, Memory)

---

## 📁 Kiểm Tra Source Code

### 4. Backend Files
- [ ] `ML-app.py` tồn tại
- [ ] `requirements.txt` chứa tất cả dependencies
- [ ] Models joblib files có sẵn:
  - [ ] `jupiter_notebook/model_ml.joblib`
  - [ ] `jupiter_notebook/model_logistic_regression.joblib`
  - [ ] `jupiter_notebook/model_random_forest.joblib`
  - [ ] `jupiter_notebook/model_xgboost.joblib`
  - [ ] `jupiter_notebook/scaler_logistic_regression.joblib`
- [ ] `Dockerfile` (backend) chính xác

### 5. Frontend Files
- [ ] `UI/pages/` chứa HTML files
  - [ ] `index.html`
  - [ ] `login.html`
  - [ ] `user_management.html`
  - [ ] `loan_management.html`
- [ ] `UI/assets/css/style.css` tồn tại
- [ ] `UI/assets/js/script.js` tồn tại
- [ ] `UI/assets/js/login-script.js` tồn tại
- [ ] `UI/Dockerfile` chính xác
- [ ] `UI/nginx.conf` chính xác

### 6. Kubernetes Files
- [ ] `k8s-secrets.yaml` chính xác
- [ ] `k8s-backend-deployment.yaml` chính xác
- [ ] `k8s-frontend-deployment.yaml` chính xác
- [ ] `k8s-ingress.yaml` chính xác (host URL)
- [ ] `.dockerignore` tồn tại

### 7. Configuration Files
- [ ] `.env.example` có mô tả rõ
- [ ] Tất cả hardcoded URLs đã xóa
- [ ] Database connection string trong `k8s-secrets.yaml`
- [ ] SECRET_KEY trong `k8s-secrets.yaml`

---

## 🔧 Chuẩn Bị Deployment

### 8. Sửa File YAML
- [ ] Thay `YOUR_PROJECT_ID` trong:
  - [ ] `k8s-backend-deployment.yaml`
  - [ ] `k8s-frontend-deployment.yaml`
- [ ] Kiểm tra URL trong `k8s-ingress.yaml` (34.87.54.108.nip.io?)
- [ ] Kiểm tra DATABASE_URL trong `k8s-secrets.yaml`

### 9. Test Local (Optional nhưng recommended)
- [ ] Build backend image locally: `docker build -t ml-backend:test .`
- [ ] Build frontend image locally: `docker build -t ml-frontend:test ./UI`
- [ ] Run backend: `docker run -p 5000:5000 ml-backend:test`
- [ ] Test health: `curl http://localhost:5000/health`

### 10. GCP Authentication
- [ ] Login vào gcloud: `gcloud auth login`
- [ ] Set project: `gcloud config set project YOUR_PROJECT_ID`
- [ ] Configure Docker auth: `gcloud auth configure-docker`
- [ ] Verify: `gcloud auth list`

---

## 🚀 Deployment Steps

### 11. Build & Push Images
- [ ] Build backend: `docker build -t gcr.io/YOUR_PROJECT_ID/ml-backend:latest .`
- [ ] Build frontend: `docker build -t gcr.io/YOUR_PROJECT_ID/ml-frontend:latest ./UI`
- [ ] Push backend: `docker push gcr.io/YOUR_PROJECT_ID/ml-backend:latest`
- [ ] Push frontend: `docker push gcr.io/YOUR_PROJECT_ID/ml-frontend:latest`

### 12. Setup Kubernetes
- [ ] Get cluster credentials: `gcloud container clusters get-credentials gke-ml-ops-02 --zone asia-southeast1-a --project YOUR_PROJECT_ID`
- [ ] Verify connection: `kubectl cluster-info`
- [ ] Check nodes: `kubectl get nodes`

### 13. Deploy
- [ ] Create secrets: `kubectl apply -f k8s-secrets.yaml`
- [ ] Deploy backend: `kubectl apply -f k8s-backend-deployment.yaml`
- [ ] Deploy frontend: `kubectl apply -f k8s-frontend-deployment.yaml`
- [ ] Deploy ingress: `kubectl apply -f k8s-ingress.yaml`

### 14. Kiểm Tra Deployment
- [ ] Check deployments: `kubectl get deployments`
- [ ] Check pods: `kubectl get pods`
- [ ] Check services: `kubectl get svc`
- [ ] Check ingress: `kubectl get ingress`
- [ ] Check backend logs: `kubectl logs -f deployment/ml-backend`
- [ ] Check frontend logs: `kubectl logs -f deployment/ml-frontend`

### 15. Test API
- [ ] Test health: `curl http://34.87.54.108.nip.io/health`
- [ ] Test docs: `curl http://34.87.54.108.nip.io/docs` (hoặc trên browser)
- [ ] Run test script: `python test_api.py http://34.87.54.108.nip.io`

---

## 🌐 Post-Deployment

### 16. Verify Services
- [ ] Frontend accessible: `http://34.87.54.108.nip.io/`
- [ ] Backend API docs: `http://34.87.54.108.nip.io/docs`
- [ ] Register test user
- [ ] Login test user
- [ ] Test prediction endpoint

### 17. Monitor
- [ ] Check pod resource usage: `kubectl top pods`
- [ ] Check node resource usage: `kubectl top nodes`
- [ ] Check for errors in logs
- [ ] Monitor response times

### 18. Database
- [ ] Verify database connection: `kubectl logs deployment/ml-backend | grep -i database`
- [ ] Check database file (if using SQLite): `kubectl exec -it <pod-name> -- ls -la /app/`

### 19. Scaling (Optional)
- [ ] Scale backend: `kubectl scale deployment ml-backend --replicas=5`
- [ ] Scale frontend: `kubectl scale deployment ml-frontend --replicas=3`
- [ ] Verify: `kubectl get deployment ml-backend ml-frontend`

---

## 🔍 Troubleshooting

### 20. Nếu Có Lỗi
- [ ] Check backend logs: `kubectl logs -f deployment/ml-backend`
- [ ] Check frontend logs: `kubectl logs -f deployment/ml-frontend`
- [ ] Check pod events: `kubectl describe pod <pod-name>`
- [ ] Check ingress: `kubectl describe ingress ml-app-ingress`
- [ ] Check services: `kubectl get endpoints ml-backend ml-frontend`

### 21. Common Issues
- [ ] **Pods not starting**: Check resource requests/limits, check logs
- [ ] **500 error from API**: Check database connection, check models loaded
- [ ] **Ingress not routing**: Check service selectors, check ingress rules
- [ ] **Models not loading**: Check path in Dockerfile, check if copy command worked

---

## 📊 Final Status Check

```bash
# Chạy command này để check tất cả
kubectl get all
kubectl get ingress
kubectl get secrets
kubectl get configmap
```

Expected output:
- ✅ `deployment.apps/ml-backend` in desired state
- ✅ `deployment.apps/ml-frontend` in desired state
- ✅ `service/ml-backend` with ClusterIP
- ✅ `service/ml-frontend` with ClusterIP
- ✅ `ingress.networking.k8s.io/ml-app-ingress` with IP/hostname
- ✅ `secret/ml-secrets` exists
- ✅ Pods running: `1/1 Ready` for all pods

---

## 🎯 Success Criteria

Deployment thành công khi:
- [ ] Tất cả pods running & ready
- [ ] Frontend accessible tại `http://34.87.54.108.nip.io/`
- [ ] Backend API accessible tại `http://34.87.54.108.nip.io/docs`
- [ ] Có thể login và sử dụng ứng dụng
- [ ] Không có lỗi trong logs
- [ ] API endpoints response thành công
- [ ] Database operations working

---

## 🧹 Cleanup (Nếu cần rollback)

```bash
# Xóa tất cả resources
kubectl delete -f k8s-*.yaml

# Hoặc xóa từng cái
kubectl delete ingress ml-app-ingress
kubectl delete deployment ml-backend ml-frontend
kubectl delete service ml-backend ml-frontend
kubectl delete secret ml-secrets
```

---

**Lưu ý**: Sau khi hoàn thành deployment, hãy giữ lại các file YAML và deployment scripts để quản lý dễ hơn trong tương lai.
