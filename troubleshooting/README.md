# Troubleshooting lab

Five deliberately broken manifests. They assume the chart is installed as release `gearloop`
in namespace `gearloop`. Apply one, investigate **without reading the answer first**, fix it, then clean up:

```bash
kubectl apply -f troubleshooting/01-image-pull.yaml
# ...investigate and fix...
kubectl delete -f troubleshooting/01-image-pull.yaml
# or remove every lab object at once:
kubectl delete deploy,svc,secret,ingress -n gearloop -l lab=troubleshooting
```

A general first pass that works for all of them:

```bash
kubectl get pods,svc,endpointslices,ingress -n gearloop
kubectl describe pod <pod> -n gearloop        # read the Events at the bottom
kubectl logs <pod> -n gearloop [--previous]
kubectl get events -n gearloop --sort-by=.lastTimestamp | tail -20
```

---

<details>
<summary><b>1. ImagePullBackOff</b> (01-image-pull.yaml)</summary>

**Symptom:** `ErrImagePull`, then `ImagePullBackOff`.

**Diagnose:** `kubectl describe pod -l app=gearloop-canary -n gearloop` shows
`manifest unknown` / `not found` for `gearloop-backend:v9.9.9-typo`.
CI only publishes commit-SHA tags, so that tag never existed.

**Fix:** use a tag that exists:
```bash
kubectl set image deploy/gearloop-canary backend=ghcr.io/<owner>/gearloop-backend:<commit-sha> -n gearloop
```
**Lesson:** immutable SHA tags make "which version is running?" answerable, but a typo is fatal; the registry is the source of truth.
</details>

<details>
<summary><b>2. Service with no endpoints</b> (02-service-selector.yaml)</summary>

**Symptom:** `kubectl run tmp --rm -it --image=busybox:1.37 -n gearloop -- wget -qO- gearloop-api-internal:8000/health` hangs or is refused.

**Diagnose:**
```bash
kubectl get endpointslices -n gearloop -l kubernetes.io/service-name=gearloop-api-internal   # no addresses
kubectl get pods -n gearloop --show-labels | grep backend    # component=backend, not api
```
**Fix:** change the selector to `app.kubernetes.io/component: backend` and re-apply.

**Lesson:** Services find pods only by labels. A selector that matches nothing is not an error; it is just empty.
</details>

<details>
<summary><b>3. Running but never Ready</b> (03-bad-db-secret.yaml)</summary>

**Symptom:** pod is `Running` with `0/1` READY and is never added to a Service.

**Diagnose:**
```bash
kubectl describe pod -l app=gearloop-staging-api -n gearloop   # Readiness probe failed: HTTP 503
kubectl exec deploy/gearloop-staging-api -n gearloop -- python -c "import urllib.request as u; print(u.urlopen('http://127.0.0.1:8000/health').read())"   # UP
kubectl port-forward deploy/gearloop-staging-api 8001:8000 -n gearloop & curl -s localhost:8001/ready
# {"status":"NOT_READY","reason":"OperationalError"}  <- DB auth failure
```
**Fix:** point the deployment at the chart's real Secret (`gearloop-db`, key `database-url`)
or correct the password in `gearloop-db-staging`, then `kubectl rollout restart deploy/gearloop-staging-api -n gearloop`.

**Lesson:** this is why `/health` (liveness) and `/ready` (readiness) are separate. A bad DB
password must stop traffic, not trigger an endless restart loop.
</details>

<details>
<summary><b>4. CrashLoopBackOff with exit code 137</b> (04-oomkilled.yaml)</summary>

**Symptom:** restarts keep climbing.

**Diagnose:**
```bash
kubectl get pod -l app=gearloop-report-worker -n gearloop -o jsonpath='{.items[0].status.containerStatuses[0].lastState.terminated}'
# {"exitCode":137,"reason":"OOMKilled",...}
```
The process allocates about 200 MiB, but `limits.memory` is 96Mi, so the kernel kills it.

**Fix:** raise the limit above real usage (for example 320Mi), or fix the code so it streams instead of buffering.
`kubectl top pod` (metrics-server) shows real usage.

**Lesson:** exit code 137 = SIGKILL. With `reason: OOMKilled` it is a memory limit, not an application bug or a failed probe.
</details>

<details>
<summary><b>5. Ingress returns 503 for /api</b> (05-ingress-wrong-port.yaml)</summary>

**Symptom:** `curl -H 'Host: beta.gearloop.local' http://$(minikube ip)/` works, but `/api/stats` gives `503 Service Temporarily Unavailable`.

**Diagnose:**
```bash
kubectl describe ingress gearloop-beta -n gearloop          # backend gearloop-backend:8080 (<error: endpoints ... not found>)
kubectl get svc gearloop-backend -n gearloop                # PORT(S) 8000/TCP
kubectl logs -n ingress-nginx deploy/ingress-nginx-controller | grep beta
```
**Fix:** use `port: {number: 8000}` (or `port: {name: http}`, as the chart does, so it cannot drift).

**Lesson:** an Ingress points at a *Service port*, not a container port. Referring to ports by name avoids this whole class of bug.
</details>
