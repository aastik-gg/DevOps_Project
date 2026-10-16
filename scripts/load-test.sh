#!/usr/bin/env bash
# Generate CPU load on the backend so the HPA scales out, and traffic for the Grafana panels.
# Runs *inside* the cluster, so it works the same on minikube and EKS.
#
#   ./scripts/load-test.sh            # 3 minutes, 20 workers
#   DURATION=300 WORKERS=40 ./scripts/load-test.sh
#   watch kubectl get hpa,pods -n gearloop      # in another terminal
set -euo pipefail

NAMESPACE="${NAMESPACE:-gearloop}"
TARGET="${TARGET:-http://gearloop-backend:8000}"
DURATION="${DURATION:-180}"
WORKERS="${WORKERS:-20}"

echo "Hitting $TARGET from $WORKERS workers for ${DURATION}s (namespace $NAMESPACE)"
kubectl run gearloop-load --rm -i --restart=Never -n "$NAMESPACE" \
  --image=busybox:1.37 \
  --overrides='{"spec":{"securityContext":{"runAsNonRoot":true,"runAsUser":65534,"seccompProfile":{"type":"RuntimeDefault"}},"containers":[{"name":"gearloop-load","image":"busybox:1.37","stdin":true,"command":["sh"],"securityContext":{"allowPrivilegeEscalation":false,"capabilities":{"drop":["ALL"]}}}]}}' \
  <<SCRIPT
end=\$((\$(date +%s) + $DURATION))
for w in \$(seq 1 $WORKERS); do
  ( while [ \$(date +%s) -lt \$end ]; do
      wget -qO- $TARGET/api/items >/dev/null 2>&1
      wget -qO- $TARGET/api/stats >/dev/null 2>&1
      wget -qO- $TARGET/api/items?q=scope >/dev/null 2>&1
    done ) &
done
wait
echo "load finished"
SCRIPT
