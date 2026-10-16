#!/usr/bin/env bash
# Generate CPU load on the backend so the HPA scales out, and traffic for the Grafana panels.
# Runs as a Job *inside* the cluster, so it works the same on minikube or any other cluster.
#
#   ./scripts/load-test.sh                         # 3 minutes, 20 workers
#   DURATION=300 WORKERS=40 ./scripts/load-test.sh
#   watch kubectl get hpa,pods -n gearloop         # in another terminal
set -euo pipefail

NAMESPACE="${NAMESPACE:-gearloop}"
TARGET="${TARGET:-http://gearloop-backend:8000}"
DURATION="${DURATION:-180}"
WORKERS="${WORKERS:-20}"

kubectl delete job gearloop-load -n "$NAMESPACE" --ignore-not-found >/dev/null
echo "Hitting $TARGET from $WORKERS workers for ${DURATION}s (namespace $NAMESPACE)"

kubectl apply -n "$NAMESPACE" -f - <<YAML
apiVersion: batch/v1
kind: Job
metadata:
  name: gearloop-load
  labels: {app: gearloop-load}
spec:
  backoffLimit: 0
  ttlSecondsAfterFinished: 300
  template:
    metadata:
      labels: {app: gearloop-load}
    spec:
      restartPolicy: Never
      securityContext:
        runAsNonRoot: true
        runAsUser: 65534
        seccompProfile: {type: RuntimeDefault}
      containers:
        - name: load
          image: busybox:1.37
          securityContext:
            allowPrivilegeEscalation: false
            capabilities: {drop: [ALL]}
          resources:
            requests: {cpu: 100m, memory: 32Mi}
            limits: {cpu: "1", memory: 128Mi}
          env:
            - {name: TARGET, value: "$TARGET"}
            - {name: DURATION, value: "$DURATION"}
            - {name: WORKERS, value: "$WORKERS"}
          command: ["sh", "-c"]
          args:
            - |
              end=\$((\$(date +%s) + DURATION))
              for w in \$(seq 1 "\$WORKERS"); do
                ( while [ "\$(date +%s)" -lt "\$end" ]; do
                    wget -qO- "\$TARGET/api/items" >/dev/null 2>&1
                    wget -qO- "\$TARGET/api/stats" >/dev/null 2>&1
                    wget -qO- "\$TARGET/api/items?q=scope" >/dev/null 2>&1
                  done ) &
              done
              wait
              echo "load finished"
YAML

kubectl wait job/gearloop-load -n "$NAMESPACE" --for=condition=complete --timeout="$((DURATION + 120))s"
kubectl logs job/gearloop-load -n "$NAMESPACE"
