 gcloud container clusters get-credentials gke-ml-ops-02 --zone asia-southeast1-a --project deploy-model-loan-prediction 
 kubectl create namespace monitoring;  kubectl apply -f jaeger-deployment.yaml 

 tắt Jaeger: kubectl scale deployment jaeger --replicas=0 -n monitoring 
 bật Jeager: kubectl scale deployment jaeger --replicas=1 -n monitoring 
 check pod jeager: kubectl get pod -n monitoring
 check namespace có service chưa: kubectl get svc -n monitoring
 Để truy cập được vào Jaeger, sử dụng port-forward: kubectl port-forward -n monitoring svc/jaeger 16686:16686
 truy cap link: localhost:16686

 gcloud compute instances stop/ start gke-gke-ml-ops-02-node-mlops-254a8a90-4gnj --zone asia-southeast1-a 
 gcloud compute instances stop/ start gke-gke-ml-ops-02-node-mlops-254a8a90-9k0g --zone asia-southeast1-a 
 gcloud compute instances stop/ start gke-gke-ml-ops-02-node-mlops-254a8a90-gn14 --zone asia-southeast1-a 

 gcloud container node-pools resize TÊN_NODE_POOL --cluster TÊN_CỤM --num-nodes 0 or 3 --zone VÙNG_CỦA_CỤM 
 gcloud container node-pools describe node-mlops  --cluster gke-ml-ops-02 --zone asia-southeast1-a

 ngrok http 8080 Tạo thành 1 "đường hầm" với Jenkins ở máy local, thay vì truy cập vào localhost:8080, chúng ta có thể truy cập Jenkins thông qua địa chỉ web được hiện ra khi nhập lệnh này.