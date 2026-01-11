 gcloud container clusters get-credentials gke-ml-ops-02 --zone asia-southeast1-a --project loan-prediction-ubuntu 
 kubectl create namespace monitoring;  kubectl apply -f jaeger-deployment.yaml 

 tắt Jaeger: kubectl scale deployment jaeger --replicas=0 -n monitoring 
 bật Jeager: kubectl scale deployment jaeger --replicas=1 -n monitoring 
 check pod jeager: kubectl get pod -n monitoring
 check namespace có service chưa: kubectl get svc -n monitoring
 Để truy cập được vào Jaeger, sử dụng port-forward: kubectl port-forward -n monitoring svc/jaeger 16686:16686
 truy cap link: localhost:16686


 gcloud container node-pools resize TÊN_NODE_POOL --cluster TÊN_CỤM --num-nodes 0 or 3 --zone VÙNG_CỦA_CỤM 

gcloud container clusters resize gke-ml-ops-02 --node-pool node-mlops --num-nodes 0 --zone asia-southeast1-a


 gcloud container node-pools describe node-mlops  --cluster gke-ml-ops-02 --zone asia-southeast1-a

 ngrok http 8080: Tạo thành 1 "đường hầm" với Jenkins ở máy local, thay vì truy cập vào localhost:8080, chúng ta có thể truy cập Jenkins thông qua địa chỉ web được hiện ra khi nhập lệnh này.

gcloud container clusters describe gke-ml-ops-02 --zone asia-southeast1-a --format="value(endpoint)": get kube URL
gcloud container clusters describe <Tên Cluster> --zone=<Tên vùng> --format="value(masterAuth.clusterCaCertificate)": get kube server certificate

// Get Access Token đại diện cho Service Account trong GCP
gcloud auth activate-service-account jenkin-serviceaccount@deploy-model-loan-prediction.iam.gserviceaccount.com --key-file=C:\Users\nguye\Downloads\deploy-model-loan-prediction-831068f9d106.json
gcloud auth print-access-token
// end

//apply ingress
kubectl apply -f ingress.yaml
//delete
kubectl delete ingress nguyen-ingress -n model-serving

uvicorn ML-app:app --reload //run api local
