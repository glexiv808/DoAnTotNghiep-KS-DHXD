#!/bin/bash

# Script triển khai ML App on GKE
# Sử dụng: ./deploy.sh <project-id> <action>
# Actions: build, push, deploy, all

set -e

PROJECT_ID=${1:-""}
ACTION=${2:-"all"}

if [ -z "$PROJECT_ID" ]; then
    echo "Usage: ./deploy.sh <PROJECT_ID> [action]"
    echo "Actions: build, push, deploy, all (default)"
    exit 1
fi

REGION="asia-southeast1-a"
CLUSTER_NAME="gke-ml-ops-02"
BACKEND_IMAGE="gcr.io/${PROJECT_ID}/ml-backend:latest"
FRONTEND_IMAGE="gcr.io/${PROJECT_ID}/ml-frontend:latest"

echo "================================"
echo "ML App Deployment Script"
echo "================================"
echo "Project ID: ${PROJECT_ID}"
echo "Backend Image: ${BACKEND_IMAGE}"
echo "Frontend Image: ${FRONTEND_IMAGE}"
echo "================================"

# Build Backend
if [ "$ACTION" = "build" ] || [ "$ACTION" = "all" ]; then
    echo "📦 Building Backend Image..."
    docker build -t ${BACKEND_IMAGE} .
    
    echo "📦 Building Frontend Image..."
    docker build -t ${FRONTEND_IMAGE} ./UI
fi

# Push Images
if [ "$ACTION" = "push" ] || [ "$ACTION" = "all" ]; then
    echo "🚀 Pushing Backend Image..."
    docker push ${BACKEND_IMAGE}
    
    echo "🚀 Pushing Frontend Image..."
    docker push ${FRONTEND_IMAGE}
fi

# Deploy to GKE
if [ "$ACTION" = "deploy" ] || [ "$ACTION" = "all" ]; then
    echo "🔗 Getting cluster credentials..."
    gcloud container clusters get-credentials ${CLUSTER_NAME} \
        --zone ${REGION} \
        --project ${PROJECT_ID}
    
    echo "📝 Creating Secrets..."
    kubectl apply -f k8s-secrets.yaml
    
    echo "🚀 Deploying Backend..."
    # Update image URL in deployment
    sed -i.bak "s|gcr.io/YOUR_PROJECT_ID|gcr.io/${PROJECT_ID}|g" k8s-backend-deployment.yaml
    kubectl apply -f k8s-backend-deployment.yaml
    
    echo "🚀 Deploying Frontend..."
    sed -i.bak "s|gcr.io/YOUR_PROJECT_ID|gcr.io/${PROJECT_ID}|g" k8s-frontend-deployment.yaml
    kubectl apply -f k8s-frontend-deployment.yaml
    
    echo "🔌 Creating Ingress..."
    kubectl apply -f k8s-ingress.yaml
    
    echo "⏳ Waiting for pods to be ready..."
    kubectl rollout status deployment/ml-backend --timeout=5m
    kubectl rollout status deployment/ml-frontend --timeout=5m
fi

echo ""
echo "================================"
echo "✅ Deployment Complete!"
echo "================================"
echo ""
echo "📊 Checking status..."
kubectl get deployments
kubectl get services
kubectl get ingress

echo ""
echo "🌐 Access your application:"
echo "   Frontend: http://34.87.54.108.nip.io/"
echo "   Backend API: http://34.87.54.108.nip.io/docs"
echo ""
echo "📋 View logs:"
echo "   Backend: kubectl logs -f deployment/ml-backend"
echo "   Frontend: kubectl logs -f deployment/ml-frontend"
