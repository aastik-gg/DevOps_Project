# Recording the walkthrough video

The rubric makes the video **mandatory** (no video = 0 for M10). Save it as `demo/presentation.mp4`.
If the file is over GitHub's 100 MB limit, attach it to a GitHub Release instead and link it from the README.
Aim for 12–18 minutes. Record at 1080p with the terminal font enlarged (Ctrl + several times).

## Before you press record

```bash
# 1. Push the repo (public) and let the first pipeline finish green. It pushes the images
#    and commits "deploy: gearloop <sha> [skip ci]" with the real image tags.
# 2. Make both GHCR packages public: GitHub → your profile → Packages → gearloop-backend /
#    gearloop-frontend → Package settings → Change visibility → Public.
git pull                                   # fetch the bot's tag-bump commit

# 3. Cluster in Argo CD mode, deploying from GitHub
minikube start
cd terraform
terraform destroy -auto-approve            # only when switching from helm mode
terraform apply -var deploy_mode=argocd -auto-approve
cd ..

# 4. Hostnames (once)
echo "$(minikube ip) gearloop.local grafana.gearloop.local argocd.gearloop.local" | sudo tee -a /etc/hosts

# 5. Logins you will need on camera
kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath='{.data.password}' | base64 -d; echo
#    Grafana: admin / change-me-gearloop

# 6. Prometheus UI (not exposed through Ingress)
kubectl port-forward -n monitoring svc/monitoring-kube-prometheus-prometheus 9090:9090 &
```

Open these browser tabs in advance: the GitHub repo, its Actions tab, the GHCR packages, http://gearloop.local,
http://argocd.gearloop.local, http://grafana.gearloop.local (GearLoop dashboard), http://localhost:9090/targets.

## Recording order (as the rubric lists it)

### 1. Slides (3–4 min): `demo/presentation.pptx`
Overview → tech stack → architecture → CI/CD → infrastructure → Kubernetes → observability → key learnings.
The speaker notes under each slide are your script.

### 2. Codebase (2 min)
Show the top of `README.md` (repository layout), then briefly:
`backend/app/main.py` (probes, routers), `backend/app/migrate.py` (advisory lock),
`frontend/Dockerfile` (multi-stage, non-root), `.github/workflows/ci-cd.yml` (jobs),
`helm/gearloop/templates/` and `values-gitops.yaml`, `terraform/*.tf`, `gitops/application.yaml`.

### 3. CI/CD (3 min): a push triggers the pipeline end to end
```bash
# a visible change, e.g. the tagline in frontend/src/components/Header.jsx
git commit -am "feat(ui): update desk tagline for the demo" && git push
```
In the Actions tab show: backend / frontend / infra jobs → `Image - backend` / `Image - frontend`
(Trivy gate output, push) → `gitops` (the tag-bump commit). Then show the SHA-tagged images in GHCR
and the Trivy results under Security → Code scanning.

### 4. Terraform (1–2 min)
```bash
cd terraform && terraform plan            # "No changes" proves the cluster matches the code
terraform state list
```
Explain that AWS is out of scope for this project, so Terraform manages the local cluster
(namespaces, quota, monitoring stack, Argo CD and the Application), and that `destroy` removes it all
(show `screenshots/22c-terraform-destroy.png` rather than destroying on camera).

### 5. Argo CD (2 min)
In http://argocd.gearloop.local: the `gearloop` app *Synced / Healthy*, its resource tree, and
History and Rollback showing the revision from the push you made in step 3 (the UI change is now live at
http://gearloop.local). Then show self-heal:
```bash
kubectl scale deploy gearloop-frontend -n gearloop --replicas=1
kubectl get deploy gearloop-frontend -n gearloop -w      # back to 2 within seconds
```

### 6. Kubernetes (1–2 min)
```bash
kubectl get pods,svc,ingress,hpa,pdb -n gearloop
helm list -A
```
Open http://gearloop.local and check out an item.

### 7. Prometheus (1 min)
http://localhost:9090/targets with `gearloop-backend` pods `UP`, and Alerts showing the 4 GearLoop rules.

### 8. Grafana + autoscaling (2 min)
```bash
./scripts/load-test.sh          # in a second terminal: watch kubectl get hpa,pods -n gearloop
```
Show the GearLoop dashboard updating (requests, latency, CPU per pod) while the HPA scales 2 → 6.

### Optional (if time allows): one troubleshooting scenario
```bash
kubectl apply -f troubleshooting/02-service-selector.yaml
kubectl get endpointslices -n gearloop -l kubernetes.io/service-name=gearloop-api-internal
kubectl delete -f troubleshooting/02-service-selector.yaml
```
