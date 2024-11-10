
kubectl get deployment istiod -n istio-system -o yaml > pilot-deployment.yaml
kubectl get deployment istio-ingressgateway -n istio-system -o yaml > ig-deployment.yaml

# make changes to sampling and add nodeaffinity to ig and istiod

kubectl apply -f pilot-deployment.yaml
kubectl apply -f ig-deployment.yaml
kubectl apply -f istio/jaeger.yaml
kubectl apply -f istio/prometheus.yaml
    