# Script Deployment cho Windows PowerShell
# Sử dụng: .\deploy.ps1 -ProjectId "loan-prediction-ubuntu" -Action "all"

param(
    [Parameter(Mandatory=$true)]
    [string]$ProjectId,
    
    [Parameter(Mandatory=$false)]
    [ValidateSet("build", "push", "deploy", "all")]
    [string]$Action = "all",
    
    [Parameter(Mandatory=$false)]
    [string]$Region = "asia-southeast1-a",
    
    [Parameter(Mandatory=$false)]
    [string]$ClusterName = "gke-ml-ops-02"
)

$ErrorActionPreference = "Stop"

$BACKEND_IMAGE = "gcr.io/${ProjectId}/ml-backend:latest"
$FRONTEND_IMAGE = "gcr.io/${ProjectId}/ml-frontend:latest"

Write-Host "================================" -ForegroundColor Cyan
Write-Host "ML App Deployment Script (Windows)" -ForegroundColor Cyan
Write-Host "================================" -ForegroundColor Cyan
Write-Host "Project ID: $ProjectId" -ForegroundColor Yellow
Write-Host "Backend Image: $BACKEND_IMAGE" -ForegroundColor Yellow
Write-Host "Frontend Image: $FRONTEND_IMAGE" -ForegroundColor Yellow
Write-Host "Action: $Action" -ForegroundColor Yellow
Write-Host "================================" -ForegroundColor Cyan
Write-Host ""

# Build Backend
if ($Action -eq "build" -or $Action -eq "all") {
    Write-Host "📦 Building Backend Image..." -ForegroundColor Green
    docker build -t $BACKEND_IMAGE .
    
    Write-Host "📦 Building Frontend Image..." -ForegroundColor Green
    docker build -t $FRONTEND_IMAGE ./UI
}

# Push Images
if ($Action -eq "push" -or $Action -eq "all") {
    Write-Host "🚀 Pushing Backend Image..." -ForegroundColor Green
    docker push $BACKEND_IMAGE
    
    Write-Host "🚀 Pushing Frontend Image..." -ForegroundColor Green
    docker push $FRONTEND_IMAGE
}

# Deploy to GKE
if ($Action -eq "deploy" -or $Action -eq "all") {
    Write-Host "🔗 Getting cluster credentials..." -ForegroundColor Green
    gcloud container clusters get-credentials $ClusterName `
        --zone $Region `
        --project $ProjectId
    
    Write-Host "📝 Creating Secrets..." -ForegroundColor Green
    kubectl apply -f k8s-secrets.yaml
    
    Write-Host "🚀 Deploying Backend..." -ForegroundColor Green
    # Update image URL in deployment
    (Get-Content k8s-backend-deployment.yaml) -replace "gcr.io/YOUR_PROJECT_ID", "gcr.io/$ProjectId" `
        | Set-Content k8s-backend-deployment.yaml.tmp
    kubectl apply -f k8s-backend-deployment.yaml.tmp
    Remove-Item k8s-backend-deployment.yaml.tmp
    
    Write-Host "🚀 Deploying Frontend..." -ForegroundColor Green
    (Get-Content k8s-frontend-deployment.yaml) -replace "gcr.io/YOUR_PROJECT_ID", "gcr.io/$ProjectId" `
        | Set-Content k8s-frontend-deployment.yaml.tmp
    kubectl apply -f k8s-frontend-deployment.yaml.tmp
    Remove-Item k8s-frontend-deployment.yaml.tmp
    
    Write-Host "🔌 Creating Ingress..." -ForegroundColor Green
    kubectl apply -f k8s-ingress.yaml
    
    Write-Host "⏳ Waiting for pods to be ready..." -ForegroundColor Green
    kubectl rollout status deployment/ml-backend --timeout=5m
    kubectl rollout status deployment/ml-frontend --timeout=5m
}

Write-Host ""
Write-Host "================================" -ForegroundColor Cyan
Write-Host "✅ Deployment Complete!" -ForegroundColor Cyan
Write-Host "================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "📊 Checking status..." -ForegroundColor Green
kubectl get deployments
kubectl get services
kubectl get ingress

Write-Host ""
Write-Host "🌐 Access your application:" -ForegroundColor Yellow
Write-Host "   Frontend: http://34.87.54.108.nip.io/" -ForegroundColor Cyan
Write-Host "   Backend API: http://34.87.54.108.nip.io/docs" -ForegroundColor Cyan
Write-Host ""
Write-Host "📋 View logs:" -ForegroundColor Yellow
Write-Host "   Backend: kubectl logs -f deployment/ml-backend" -ForegroundColor Cyan
Write-Host "   Frontend: kubectl logs -f deployment/ml-frontend" -ForegroundColor Cyan
