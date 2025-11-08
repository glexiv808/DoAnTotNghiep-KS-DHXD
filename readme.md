 gcloud container clusters get-credentials gke-ml-ops-02 --zone asia-southeast1-a --project deploy-model-loan-prediction </br>
 kubectl create namespace monitoring;  kubectl apply -f jaeger-deployment.yaml </br>

 tắt Jaeger: kubectl scale deployment jaeger --replicas=0 -n monitoring </br>
 bật Jeager: kubectl scale deployment jaeger --replicas=1 -n monitoring </br> 