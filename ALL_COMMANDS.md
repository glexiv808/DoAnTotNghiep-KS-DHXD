# Tất cả các lệnh triển khai - Copy & Paste

## =============================================================
## BƯỚC 1: SETUP - Thay YOUR_PROJECT_ID bằng GCP Project ID
## =============================================================

# Thiết lập biến môi trường
$PROJECT_ID = "YOUR_PROJECT_ID"  # Thay này!!!
$CLUSTER = "gke-ml-ops-02"
$ZONE = "asia-southeast1-a"
$BACKEND_IMAGE = "gcr.io/$PROJECT_ID/ml-backend:latest"
$FRONTEND_IMAGE = "gcr.io/$PROJECT_ID/ml-frontend:latest"

# Hoặc trên Linux/Mac:
# export PROJECT_ID="YOUR_PROJECT_ID"
# export CLUSTER="gke-ml-ops-02"
# export ZONE="asia-southeast1-a"
# export BACKEND_IMAGE="gcr.io/${PROJECT_ID}/ml-backend:latest"
# export FRONTEND_IMAGE="gcr.io/${PROJECT_ID}/ml-frontend:latest"

## =============================================================
## BƯỚC 2: BUILD DOCKER IMAGES
## =============================================================

# Build Backend
docker build -t $BACKEND_IMAGE .

# Build Frontend
docker build -t $FRONTEND_IMAGE ./UI

## =============================================================
## BƯỚC 3: PUSH IMAGES LÊN CONTAINER REGISTRY
## =============================================================

# Configure Docker authentication with gcloud
gcloud auth configure-docker

# Push Backend
docker push $BACKEND_IMAGE

# Push Frontend
docker push $FRONTEND_IMAGE

## =============================================================
## BƯỚC 4: SETUP KUBERNETES CLUSTER
## =============================================================

# Get cluster credentials
gcloud container clusters get-credentials $CLUSTER `
    --zone $ZONE `
    --project $PROJECT_ID

# Verify connection
kubectl cluster-info

## =============================================================
## BƯỚC 5: TẠO KUBERNETES SECRETS
## =============================================================

# Apply secrets & configmap
kubectl apply -f k8s-secrets.yaml

# Verify
kubectl get secrets ml-secrets
kubectl describe secret ml-secrets

## =============================================================
## BƯỚC 6: DEPLOY BACKEND
## =============================================================

# Sửa image URL trong k8s-backend-deployment.yaml
# Thay "gcr.io/YOUR_PROJECT_ID" bằng "gcr.io/$PROJECT_ID"

# Apply deployment
kubectl apply -f k8s-backend-deployment.yaml

# Check status
kubectl get deployments ml-backend
kubectl get pods -l app=ml-backend
kubectl logs -f deployment/ml-backend

# Wait for rollout
kubectl rollout status deployment/ml-backend --timeout=5m

## =============================================================
## BƯỚC 7: DEPLOY FRONTEND
## =============================================================

# Sửa image URL trong k8s-frontend-deployment.yaml
# Thay "gcr.io/YOUR_PROJECT_ID" bằng "gcr.io/$PROJECT_ID"

# Apply deployment
kubectl apply -f k8s-frontend-deployment.yaml

# Check status
kubectl get deployments ml-frontend
kubectl get pods -l app=ml-frontend
kubectl logs -f deployment/ml-frontend

# Wait for rollout
kubectl rollout status deployment/ml-frontend --timeout=5m

## =============================================================
## BƯỚC 8: DEPLOY INGRESS
## =============================================================

kubectl apply -f k8s-ingress.yaml

# Check Ingress status
kubectl get ingress ml-app-ingress
kubectl describe ingress ml-app-ingress

## =============================================================
## BƯỚC 9: KIỂM TRA DEPLOYMENT
## =============================================================

# Xem tất cả resources
kubectl get all

# Xem Services
kubectl get svc

# Xem Pods
kubectl get pods -o wide

# Xem Ingress
kubectl get ingress -o wide

## =============================================================
## BƯỚC 10: TEST API
## =============================================================

# Test health endpoint
curl http://34.87.54.108.nip.io/health

# Hoặc dùng script test
python test_api.py http://34.87.54.108.nip.io

## =============================================================
## BƯỚC 11: TRUY CẬP ỨNG DỤNG
## =============================================================

# Frontend
# http://34.87.54.108.nip.io/

# Backend API Docs (Swagger)
# http://34.87.54.108.nip.io/docs

# Metrics
# http://34.87.54.108.nip.io/metrics

## =============================================================
## XỬ LÝ VẤN ĐỀ (TROUBLESHOOTING)
## =============================================================

# Xem logs backend
kubectl logs -f deployment/ml-backend --all-containers=true

# Xem logs frontend
kubectl logs -f deployment/ml-frontend

# Xem chi tiết pod
kubectl describe pod <POD_NAME>

# Port forward để debug local
kubectl port-forward svc/ml-backend 5000:80
# Hoặc: kubectl port-forward svc/ml-frontend 8080:80

# Restart deployment
kubectl rollout restart deployment/ml-backend
kubectl rollout restart deployment/ml-frontend

# Scale replicas
kubectl scale deployment ml-backend --replicas=5
kubectl scale deployment ml-frontend --replicas=3

## =============================================================
## CLEANING UP (XÓA DEPLOYMENT)
## =============================================================

# Xóa Ingress
kubectl delete ingress ml-app-ingress

# Xóa Services
kubectl delete svc ml-backend ml-frontend

# Xóa Deployments
kubectl delete deployment ml-backend ml-frontend

# Xóa Secrets
kubectl delete secret ml-secrets

# Hoặc xóa tất cả một lần
kubectl delete -f k8s-*.yaml

## =============================================================
## ADVANCED COMMANDS
## =============================================================

# Exec vào pod để debug
kubectl exec -it <POD_NAME> -- /bin/sh

# Copy file từ pod
kubectl cp <POD_NAME>:/app/ml_service.db ./ml_service.db

# View events
kubectl get events --sort-by='.lastTimestamp'

# Monitor pod resource usage
kubectl top nodes
kubectl top pods

# Describe node resources
kubectl describe node <NODE_NAME>

# View pod environment variables
kubectl exec <POD_NAME> -- env | grep DATABASE_URL

## =============================================================
## JAEGER TRACING (OPTIONAL)
## =============================================================

# Port forward Jaeger
kubectl port-forward -n monitoring svc/jaeger 16686:16686

# Access: http://localhost:16686

## =============================================================
## PROMETHEUS MONITORING (OPTIONAL)
## =============================================================

# Port forward Prometheus
kubectl port-forward -n monitoring svc/prometheus 9090:9090

# Access: http://localhost:9090

## =============================================================
## GKE CLUSTER MANAGEMENT
## =============================================================

# Resize cluster
gcloud container clusters resize $CLUSTER `
    --num-nodes 5 `
    --zone $ZONE `
    --project $PROJECT_ID

# List node pools
gcloud container node-pools list --cluster=$CLUSTER --zone=$ZONE --project=$PROJECT_ID

# Resize specific node pool
gcloud container node-pools create <POOL_NAME> `
    --cluster=$CLUSTER `
    --zone=$ZONE `
    --project=$PROJECT_ID

## =============================================================
## DOCKER IMAGE MANAGEMENT
## =============================================================

# List local images
docker images | grep ml-

# Remove image
docker rmi $BACKEND_IMAGE
docker rmi $FRONTEND_IMAGE

# Tag image differently
docker tag $BACKEND_IMAGE gcr.io/$PROJECT_ID/ml-backend:v1.0.0
docker push gcr.io/$PROJECT_ID/ml-backend:v1.0.0

## =============================================================
## HELM (OPTIONAL - For advanced deployments)
## =============================================================

# Create Helm chart
helm create ml-app

# Install using Helm
helm install ml-release ./ml-app

# Upgrade release
helm upgrade ml-release ./ml-app

# Uninstall release
helm uninstall ml-release
