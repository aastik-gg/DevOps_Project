#!/usr/bin/env bash
# Full local environment: minikube + ingress + metrics-server, then Terraform installs
# the namespace, kube-prometheus-stack and the GearLoop chart.
#
#   ./scripts/minikube-up.sh
#   (cd terraform && terraform destroy)     # tear everything down again
set -euo pipefail
cd "$(dirname "$0")/.."

minikube status >/dev/null 2>&1 || minikube start --cpus=4 --memory=6g
minikube addons enable ingress
minikube addons enable metrics-server

echo "==> Building images inside minikube"
minikube image build -t gearloop-backend:local ./backend
minikube image build -t gearloop-frontend:local ./frontend

echo "==> Terraform: namespace, monitoring stack, GearLoop release"
terraform -chdir=terraform init -input=false
terraform -chdir=terraform apply -input=false -auto-approve
helm test gearloop -n gearloop

ip=$(minikube ip)
cat <<MSG

Add to /etc/hosts:
  $ip gearloop.local grafana.gearloop.local

App:     http://gearloop.local
API:     http://gearloop.local/docs
Grafana: http://grafana.gearloop.local   (admin / change-me-gearloop) -> Dashboards -> "GearLoop - Lab Equipment Desk"
MSG
