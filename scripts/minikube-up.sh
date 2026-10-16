#!/usr/bin/env bash
# Full local Kubernetes environment: minikube + ingress + metrics-server + monitoring + GearLoop.
set -euo pipefail
cd "$(dirname "$0")/.."

minikube status >/dev/null 2>&1 || minikube start --cpus=4 --memory=6g
minikube addons enable ingress
minikube addons enable metrics-server

echo "==> Building images inside minikube's Docker"
minikube image build -t gearloop-backend:local ./backend
minikube image build -t gearloop-frontend:local ./frontend

echo "==> Monitoring stack (Prometheus Operator CRDs are needed by the chart's ServiceMonitor)"
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts >/dev/null 2>&1 || true
helm repo update prometheus-community >/dev/null
helm upgrade --install monitoring prometheus-community/kube-prometheus-stack \
  -n monitoring --create-namespace -f monitoring/kube-prometheus-stack-values.yaml --wait --timeout 10m

echo "==> GearLoop"
kubectl apply -f k8s/
helm upgrade --install gearloop ./helm/gearloop -n gearloop -f helm/gearloop/values-local.yaml --wait --timeout 5m
helm test gearloop -n gearloop

ip=$(minikube ip)
cat <<MSG

Add to /etc/hosts:
  $ip gearloop.local grafana.gearloop.local

App:     http://gearloop.local
API:     http://gearloop.local/docs
Grafana: http://grafana.gearloop.local   (admin / change-me-gearloop) -> Dashboards -> "GearLoop - Lab Equipment Desk"
MSG
