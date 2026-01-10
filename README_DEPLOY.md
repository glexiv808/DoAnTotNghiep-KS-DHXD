# ML Loan Prediction Service

## 📋 Mô Tả Dự Án
Hệ thống dự đoán khoản vay sử dụng Machine Learning, bao gồm:
- **Backend**: FastAPI với ML models (Logistic Regression, Random Forest, XGBoost)
- **Frontend**: Web UI để quản lý người dùng và xử lý hóa đơn vay
- **Database**: SQLite (development) / PostgreSQL (production)
- **Monitoring**: Jaeger (tracing), Prometheus (metrics)
- **Deployment**: Kubernetes (GKE)

---

## 🚀 Quick Start - Deployment

### Prerequisites
- Docker & Docker Compose
- kubectl
- gcloud CLI (để deploy lên GCP)
- GCP Project

### 1️⃣ Build & Push Docker Images

#### Option A: Dùng Script PowerShell (Windows)
```powershell
.\deploy.ps1 -ProjectId "YOUR_PROJECT_ID" -Action "build"
.\deploy.ps1 -ProjectId "YOUR_PROJECT_ID" -Action "push"
.\deploy.ps1 -ProjectId "YOUR_PROJECT_ID" -Action "deploy"

# Hoặc deploy tất cả một lúc
.\deploy.ps1 -ProjectId "YOUR_PROJECT_ID" -Action "all"
```

#### Option B: Dùng Script Bash (Linux/Mac)
```bash
chmod +x deploy.sh
./deploy.sh YOUR_PROJECT_ID all
```

#### Option C: Dùng Manual Commands
```bash
# Build Backend
docker build -t gcr.io/YOUR_PROJECT_ID/ml-backend:latest .

# Build Frontend
docker build -t gcr.io/YOUR_PROJECT_ID/ml-frontend:latest ./UI

# Push to Container Registry
docker push gcr.io/YOUR_PROJECT_ID/ml-backend:latest
docker push gcr.io/YOUR_PROJECT_ID/ml-frontend:latest
```

### 2️⃣ Deploy lên GKE

```bash
# Kết nối với Kubernetes cluster
gcloud container clusters get-credentials gke-ml-ops-02 --zone asia-southeast1-a --project YOUR_PROJECT_ID

# Tạo Secrets & ConfigMap
kubectl apply -f k8s-secrets.yaml

# Deploy Backend
kubectl apply -f k8s-backend-deployment.yaml

# Deploy Frontend
kubectl apply -f k8s-frontend-deployment.yaml

# Deploy Ingress
kubectl apply -f k8s-ingress.yaml
```

### 3️⃣ Kiểm Tra Deployment

```bash
# Xem status Deployments
kubectl get deployments
kubectl get pods
kubectl get svc

# Xem Ingress
kubectl get ingress

# Xem logs
kubectl logs -f deployment/ml-backend
kubectl logs -f deployment/ml-frontend
```

---

## 🔗 Truy Cập Ứng Dụng

- **Frontend**: http://34.87.54.108.nip.io/
- **Backend API Docs**: http://34.87.54.108.nip.io/docs
- **Metrics**: http://34.87.54.108.nip.io/metrics

---

## 📁 Cấu Trúc Dự Án

```
.
├── ML-app.py                          # Backend FastAPI main app
├── app.py                             # Tracing setup
├── Dockerfile                         # Backend Docker image
├── requirements.txt                   # Python dependencies
│
├── UI/                                # Frontend
│   ├── Dockerfile                     # Frontend Docker image
│   ├── nginx.conf                     # Nginx configuration
│   ├── assets/
│   │   ├── css/                       # Stylesheets
│   │   └── js/                        # JavaScript files
│   └── pages/                         # HTML pages
│
├── jupiter_notebook/                  # ML Models & Training
│   ├── model_ml.joblib
│   ├── model_logistic_regression.joblib
│   ├── model_random_forest.joblib
│   ├── model_xgboost.joblib
│   └── ML_Loan_Classification.ipynb
│
├── k8s-*.yaml                         # Kubernetes manifests
├── deploy.ps1                         # Windows PowerShell deployment script
├── deploy.sh                          # Bash deployment script
├── DEPLOYMENT_GUIDE.md                # Detailed deployment guide
└── README.md                          # This file
```

---

## 🗄️ Database Configuration

### SQLite (Default - Development)
```
DATABASE_URL=sqlite:///./ml_service.db
```

### PostgreSQL (Production)
```
DATABASE_URL=postgresql://user:password@postgres.default.svc.cluster.local:5432/ml_db
```

### MySQL
```
DATABASE_URL=mysql+pymysql://user:password@mysql.default.svc.cluster.local:3306/ml_db
```

**Để thay đổi database:**
1. Sửa `k8s-secrets.yaml`
2. Chạy: `kubectl apply -f k8s-secrets.yaml`
3. Restart pods: `kubectl rollout restart deployment/ml-backend`

---

## 🔧 API Endpoints

### Public Endpoints
- `POST /register` - Đăng ký tài khoản
- `POST /login` - Đăng nhập
- `POST /predict` - Dự đoán khoản vay

### Protected Endpoints
- `GET /profile` - Lấy thông tin user
- `POST /process-loans` - Xử lý danh sách hóa đơn vay
- `GET /sessions/{session_id}/results` - Lấy kết quả xử lý

### Admin Endpoints
- `GET /admin/users` - Danh sách user
- `DELETE /admin/users/{user_id}` - Xóa user
- `POST /admin/users` - Tạo user mới

---

## 📊 Monitoring

### Jaeger Tracing
```bash
# Port forward Jaeger
kubectl port-forward -n monitoring svc/jaeger 16686:16686

# Truy cập: http://localhost:16686
```

### Prometheus Metrics
```bash
# Xem metrics
curl http://34.87.54.108.nip.io/metrics
```

---

## 🐛 Troubleshooting

### Lỗi 500 khi gọi API

1. **Kiểm tra logs backend:**
```bash
kubectl logs -f deployment/ml-backend
```

2. **Kiểm tra database connection:**
```bash
kubectl describe secret ml-secrets
```

3. **Kiểm tra models được load:**
```bash
kubectl exec -it <pod-name> -- ls -la /app/model_*.joblib
```

### Pods không start

```bash
# Xem chi tiết lỗi
kubectl describe pod <pod-name>

# Xem logs
kubectl logs <pod-name>
```

### Ingress không hoạt động

```bash
# Kiểm tra Ingress status
kubectl describe ingress ml-app-ingress

# Kiểm tra service connectivity
kubectl get endpoints ml-backend ml-frontend
```

---

## 🔑 Environment Variables

Tạo file `.env` hoặc sửa `k8s-secrets.yaml`:

```env
# Database
DATABASE_URL=sqlite:///./ml_service.db

# Security
SECRET_KEY=your-secret-key-here
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Jaeger
JAEGER_HOST=jaeger.monitoring.svc.cluster.local
JAEGER_PORT=6831

# Logging
LOG_LEVEL=INFO
```

---

## 📚 Documentation

- [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md) - Hướng dẫn triển khai chi tiết
- [ADMIN_CREATION_GUIDE.md](ADMIN_CREATION_GUIDE.md) - Hướng dẫn tạo tài khoản admin

---

## 🔄 CI/CD

### Jenkinsfile
```bash
# File: Jenkinsfile
# Sử dụng để tự động build & deploy qua Jenkins
```

### Terraform
```bash
# File: main.tf
# Sử dụng để quản lý infrastructure on GCP
```

---

## 🛠️ Development Setup (Local)

### Cài đặt Dependencies
```bash
pip install -r requirements.txt
```

### Chạy Backend Locally
```bash
python ML-app.py
# hoặc
uvicorn ML-app:app --reload
```

### Chạy Frontend Locally
```bash
# Dùng Python HTTP Server
python -m http.server 8000 --directory UI

# Hoặc dùng Live Server extension (VS Code)
```

---

## 📝 License

MIT License

---

## 👤 Author

Đô án tốt nghiệp - Khoa Đại Học Xây Dựng (DHXD)

---

## ✅ Checklist Deploy

- [ ] Sửa `YOUR_PROJECT_ID` trong tất cả file YAML
- [ ] Build Docker images
- [ ] Push images lên Container Registry
- [ ] Tạo Kubernetes Secret cho database
- [ ] Deploy Backend
- [ ] Deploy Frontend
- [ ] Deploy Ingress
- [ ] Kiểm tra pods running
- [ ] Test API endpoints
- [ ] Test Frontend UI
- [ ] Kiểm tra Jaeger tracing
- [ ] Kiểm tra Prometheus metrics

---

## 📞 Support

Nếu gặp vấn đề, hãy:
1. Kiểm tra logs: `kubectl logs -f deployment/ml-backend`
2. Xem status pods: `kubectl get pods`
3. Xem chi tiết: `kubectl describe pod <pod-name>`
4. Kiểm tra DEPLOYMENT_GUIDE.md
