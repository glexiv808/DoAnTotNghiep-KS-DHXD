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
gcloud auth activate-service-account jenkins-serviceaccount@loan-prediction-ubuntu.iam.gserviceaccount.com --key-file=/home/nguyennd808/Downloads/loan-prediction-ubuntu-89aa573db8b8.json
gcloud auth print-access-token
// end

//apply ingress
kubectl apply -f ingress.yaml
//delete
kubectl delete ingress nguyen-ingress -n model-serving

uvicorn ML-app:app --reload //run api local

//khoi dong lai pod
1: kubectl rollout restart deployment/loan-prediction-deployment -n model-serving

2: kubectl rollout status deployment/loan-prediction-deployment -n model-serving

3: kubectl get pods -n model-serving -o wide
//end khoi dong


//Monitor
model_request_total: dạng counter, đếm số request được gửi tới Model, cả các request bị lỗi
ml_prediction_duration_seconds: dạng historgram, đo thời gian thực hiện request
ml_errors_total: dạng counter, đếm số request bị lỗi gửi tới Model

rate(model_request_total[6m]) * 6 *60: chúng ta sẽ nhận được số request trung bình nhận được ( từ 1 giây nhận được bao nhiêu Request rồi nhân lên 6 phút ) ở mỗi Pod trong 6 phút gần nhất
ml_prediction_duration_seconds_sum: ta sẽ được tổng thời gian xử lý các request, kể cả các request bị lỗi, từ lúc hoạt động tới hiện tại của mỗi Pod.
increase(ml_prediction_duration_seconds_sum[5m]): sẽ nhận được tổng thời gian xử lý tất cả các request trong 5 phút gần nhất của mỗi Pod.
ml_prediction_duration_seconds_count sẽ nhận được tổng số request nhận được ở mỗi Pod từ lúc khởi động tới hiện tại.

Để tạo 1 Dashboard nhỏ thể hiện mức độ Memory Usage (tiêu tốn RAM) của các Pod
(node_memory_MemTotal_bytes - node_memory_MemAvailable_bytes) / 1024 / 1024 / 1024 
với node_memory_MemTotal_bytes là tổng RAM của node (tính bằng bytes) 4112039936, 
node_memory_MemAvailable_bytes là RAM còn trống có thể sử dụng ngay (bytes) 2994651136, 
trừ đi cho nhau chúng ta ra được số RAM đang được sử dụng của Pod đó


kubectl port-forward svc/prometheus-grafana -n monitoring  3000:80
kubectl port-forward -n monitoring svc/prometheus-kube-prometheus-prometheus 9090:909

