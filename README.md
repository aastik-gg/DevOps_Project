# GearLoop: Lab Equipment Desk

GearLoop tracks shared lab equipment: oscilloscopes, cameras, dev kits, tools.
Staff register items. Students check them out for a set number of days and return them.
The desk sees what is available, what is on loan, what is **overdue**, and what is waiting for repair.

This repository is my **Session 21 DevOps capstone**. It takes the app from a laptop
to a monitored Kubernetes deployment:

> React + Vite → FastAPI → PostgreSQL (SQLAlchemy + Alembic) → pytest → Docker → GitHub Actions →
> Trivy → GHCR → GitOps (Argo CD) → Terraform → Helm → Kubernetes (minikube) → Ingress → HPA → Prometheus + Grafana → troubleshooting

The DevOps layer follows the course architecture. The application domain, the code and these design choices are my own.

![GearLoop dashboard](screenshots/01-dashboard.png)

*All screenshots in this README were captured from the running app and cluster; the full set is in [`screenshots/`](screenshots).*

**Demo material** is in [`demo/`](demo): the slide deck ([`presentation.pptx`](demo/presentation.pptx), also as
[`slides.pdf`](demo/slides.pdf)) and the walkthrough video, recorded following [`demo/RECORDING-GUIDE.md`](demo/RECORDING-GUIDE.md).

| Area | Course reference (TaskBoard) | GearLoop |
|---|---|---|
| Domain | single `tasks` table | `items` + `loans` (one-to-many), derived status (available / on loan / overdue / maintenance) |
| Migrations | 1 revision, run in the container CMD | 2 revisions, applied by `python -m app.migrate`: compose runs it as a one-shot `migrate` service, Kubernetes as a backend **initContainer** holding a **Postgres advisory lock**, so replicas take turns instead of racing. CI runs `alembic check` against real Postgres to catch model/migration drift |
| Data integrity | none | partial unique index: an item can never have two open loans, even under concurrent checkouts |
| Metrics | HTTP metrics only | HTTP metrics **plus business metrics** read from the DB at scrape time, so they agree across replicas and survive restarts: `gearloop_items{status}`, `gearloop_checkouts_last_24h{category}`; plus per-pod counters `gearloop_checkouts_total`, `gearloop_returns_total{late}` |
| Grafana | install only | dashboard shipped **as code** in the chart (ConfigMap picked up by the Grafana sidecar) + `PrometheusRule` alerts |
| Containers | frontend runs as root | both images non-root (backend uid 10001, unprivileged nginx uid 101); read-only root FS in Kubernetes; pip removed from the runtime image |
| Kubernetes | Deployment + Service | Pod Security `restricted` namespace, StatefulSet Postgres, PDBs, NetworkPolicy (only backend may reach Postgres), startup/readiness/liveness probes, `helm test` smoke test |
| CI | single job, tag-pinned actions | parallel backend / frontend / IaC jobs, matrix image build, Trivy SARIF to the Security tab + blocking gate, all actions **pinned to commit SHAs** |
| Deploy | `helm upgrade` from CI with a kubeconfig secret | **GitOps**: CI only commits the new image tag to Git; **Argo CD** inside the cluster pulls it, so CI never holds cluster credentials |
| Terraform | AWS VPC + EKS modules | no cloud account needed: Terraform owns the **local cluster's** namespaces, quota and both Helm releases (monitoring + app), so `plan` / `apply` / `destroy` actually run, and `destroy` leaves nothing behind |

## Tech stack

| Layer | Tools |
|---|---|
| Frontend | React 19, Vite 8, plain CSS, vitest; served by nginx (unprivileged) |
| Backend | Python 3.12, FastAPI, SQLAlchemy 2, Pydantic, Alembic, Uvicorn, prometheus-fastapi-instrumentator |
| Database | PostgreSQL 17 |
| Quality | pytest, ruff, `alembic check`, actionlint, helm lint, terraform validate |
| Containers | Docker (multi-stage), Docker Compose, GitHub Container Registry |
| CI/CD | GitHub Actions (SHA-pinned actions), Trivy, GitOps with Argo CD |
| Infrastructure as Code | Terraform (kubernetes, helm, random providers) |
| Kubernetes | minikube, Helm 3, ingress-nginx, metrics-server, HPA, PDB, NetworkPolicy, Pod Security Admission |
| Observability | kube-prometheus-stack: Prometheus, Grafana, Alertmanager, ServiceMonitor, PrometheusRule |

---

## Architecture

```text
 Developer ── git push ──► GitHub ──► GitHub Actions
                                       ├─ backend : ruff · alembic upgrade/check on Postgres · pytest
                                       ├─ frontend: vitest · vite build
                                       ├─ infra   : helm lint/template · terraform fmt/validate
                                       ├─ images (matrix: backend, frontend)
                                       │    build ─► Trivy (SARIF + HIGH/CRITICAL gate) ─► push ghcr.io/…:<commit-sha>
                                       └─ gitops: commit the new <commit-sha> into helm/gearloop/values-gitops.yaml
                                                                                              │ Argo CD polls Git
   Terraform (kubernetes + helm providers): namespaces, quota, kube-prometheus-stack,          │ and syncs the chart
   Argo CD + Application (or the gearloop release directly in helm mode)                      ▼
 Browser ─► Ingress (nginx) ─┬─ /            ─► frontend Service ─► nginx pods ×2 (React build)
                             └─ /api, /docs  ─► backend Service  ─► FastAPI pods ×2..6 (HPA on CPU)
                                                  initContainer: app.migrate ─┤            ▲
                                                  (Alembic + advisory lock)   │            │ scrape /metrics (ServiceMonitor)
                                                                        ▼            │
                                                         PostgreSQL StatefulSet + PVC   Prometheus ─► Grafana dashboard
                                                         (NetworkPolicy-protected)       └─► PrometheusRule alerts
```

## Repository layout

```text
gearloop/
├── backend/                  FastAPI app
│   ├── app/                  main.py, routers/ (items, loans, stats), models, schemas, metrics, migrate, seed
│   ├── alembic/versions/     0001_create_items, 0002_create_loans
│   ├── tests/                pytest (SQLite in-memory, never the real DB)
│   ├── Dockerfile            multi-stage, non-root, no pip at runtime
│   └── pytest.ini · ruff.toml · requirements*.txt
├── frontend/                 React 19 + Vite, plain CSS, vitest
│   ├── Dockerfile            Node build stage → nginx-unprivileged runtime
│   └── nginx.conf.template   SPA routing, /api proxy, security headers, /healthz
├── docker-compose.yml        postgres → migrate (one-shot) → backend → frontend
├── .github/workflows/ci-cd.yml
├── terraform/                namespace.tf · monitoring.tf · app.tf · argocd.tf · variables.tf · outputs.tf · terraform.tfvars.example
├── helm/gearloop/            chart + values-local.yaml (minikube) + values-gitops.yaml (Argo CD, tags bumped by CI)
│                             + values-prod.yaml (GHCR images) + dashboards/gearloop.json
├── gitops/                   Argo CD values + the GearLoop Application manifest
├── k8s/                      namespace (Pod Security restricted) + ResourceQuota/LimitRange
├── monitoring/               kube-prometheus-stack values
├── troubleshooting/          5 broken manifests + guided README
├── scripts/                  minikube-up.sh · load-test.sh
├── screenshots/              every screenshot used in this README
└── demo/                     presentation.pptx · slides.pdf · walkthrough video · RECORDING-GUIDE.md
```

---

## 1. The application

### API

| Method | Path | Purpose |
|---|---|---|
| GET | `/health` | liveness: process is up (no DB call) |
| GET | `/ready` | readiness: DB reachable **and** migrated (503 otherwise) |
| GET | `/metrics` | Prometheus metrics |
| GET | `/api/stats` | counts by status, utilisation %, checkouts in the last 7 days, categories |
| GET | `/api/items?status=&q=` | list / filter / search equipment |
| GET | `/api/items/{id}` | one item, including its active loan |
| POST | `/api/items` | register equipment (409 on duplicate asset tag) |
| PUT | `/api/items/{id}` | update location / condition / notes (`NEEDS_REPAIR` → maintenance) |
| DELETE | `/api/items/{id}` | remove (409 while on loan) |
| GET | `/api/loans?active=` | loan history / open loans |
| POST | `/api/loans` | check out `{item_id, borrower, purpose, days}` (409 if unavailable, max 30 days) |
| POST | `/api/loans/{id}/return` | check in |

Swagger UI: `/docs`.

| Interactive API docs | Checking out an item from Swagger (201 Created) |
|---|---|
| <img src="screenshots/16-swagger-docs.png" alt="Swagger docs"> | <img src="screenshots/17-swagger-checkout.png" alt="Swagger checkout request"> |

### UI

A light, card-based "equipment desk". It has a status summary strip with a utilisation bar, filter chips, search,
check-out / return / edit / delete dialogs, a recent-activity panel, toasts for API errors, and loading/empty/offline
states. It is responsive down to 360px.

| | |
|---|---|
| **Filter by status** (overdue) | **Search** across name, tag and category |
| <img src="screenshots/03-filter-overdue.png" alt="Overdue filter"> | <img src="screenshots/04-search.png" alt="Search"> |
| **Register equipment** | **Check out** to a borrower for 1–30 days |
| <img src="screenshots/05-add-equipment-dialog.png" alt="Add equipment dialog"> | <img src="screenshots/07-checkout-dialog.png" alt="Checkout dialog"> |
| **On loan**: borrower, due date, activity feed, toast | **Return**: in-app confirm, no browser `confirm()` |
| <img src="screenshots/08-checked-out.png" alt="Item checked out"> | <img src="screenshots/09-return-confirm.png" alt="Return confirmation"> |
| **Edit**: *Needs repair* moves the item to Maintenance | **API errors surface as toasts** (duplicate asset tag → 409) |
| <img src="screenshots/10-edit-dialog.png" alt="Edit dialog"> | <img src="screenshots/11-validation-error.png" alt="Duplicate asset tag error"> |
| **Delete** (blocked by the API while on loan) | **Backend down**: clear error state with Retry |
| <img src="screenshots/12-delete-confirm.png" alt="Delete confirmation"> | <img src="screenshots/15-backend-offline.png" alt="Backend offline state"> |

<p align="center"><img src="screenshots/13-mobile.png" alt="Mobile view" width="280">&nbsp;&nbsp;<img src="screenshots/14-mobile-checkout.png" alt="Mobile checkout" width="280"><br><em>Mobile (390px): stacked summary, scrollable filter chips, full-width dialogs</em></p>

## 2. Run locally with Docker Compose

```bash
docker compose up --build
```

| URL | What |
|---|---|
| http://localhost:3000 | GearLoop UI (seeded with 10 demo items, 3 loans, 1 overdue) |
| http://localhost:8000/docs | Swagger |
| http://localhost:8000/metrics | Prometheus metrics |

`docker compose down` stops the stack. `docker compose down -v` also deletes the database volume.

The `migrate` service runs `python -m app.migrate --seed` once and exits.
`backend` starts only after it finishes successfully, and `frontend` starts only after the backend is healthy.

<img src="screenshots/20-docker-compose.png" alt="docker compose up output">

### Without Docker

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
export DATABASE_URL='postgresql+psycopg://gearloop:gearloop@localhost:5432/gearloop'
python -m app.migrate --seed
uvicorn app.main:app --reload --port 8000

cd ../frontend && npm ci && npm run dev     # http://localhost:5173, proxies /api to :8000
```

## 3. Tests

```bash
cd backend && pytest -v        # 21 tests: health/ready/metrics, item CRUD + validation, loans, overdue, seed
cd frontend && npm test        # vitest: date/overdue formatting helpers
```

`tests/conftest.py` points the app at an in-memory SQLite database and overrides the `get_db` dependency.
The tests never touch PostgreSQL. CI separately runs the real Alembic migrations against a Postgres service
container, and `alembic check` fails the build if the models and migrations disagree.

<img src="screenshots/18-pytest.png" alt="pytest output">

<img src="screenshots/19-frontend-tests-build.png" alt="vitest and vite build" width="640">

## 4. Docker images

| Image | Base | User | Notes |
|---|---|---|---|
| `gearloop-backend` | `python:3.12-slim` (multi-stage venv) | `10001` | no pip/setuptools at runtime, HEALTHCHECK on `/health`, migrations not baked into CMD |
| `gearloop-frontend` | `node:22-alpine` → `nginx-unprivileged:1.29-alpine` | `101` | listens on 8080, `/api` upstream set by `API_UPSTREAM` env var |

## 5. CI/CD (`.github/workflows/ci-cd.yml`)

```text
backend ─┐
frontend ├─► images [backend, frontend] ──────────────────────► gitops (main only)
infra ───┘     build → Trivy SARIF → Trivy gate → push :<sha>     bump tags in values-gitops.yaml, commit [skip ci]
```

* Runs on every push and PR to `main`. Images are **pushed only from `main`**, tagged with the full commit SHA (never `latest`).
* Every action is pinned to a commit SHA, so a hijacked tag cannot change what runs.
* **Deployment is pull-based (GitOps).** The `gitops` job rewrites the two image tags in `helm/gearloop/values-gitops.yaml`
  to the commit SHA and pushes that commit back to `main` with `[skip ci]` (so it does not trigger another run).
  Argo CD, running inside the cluster, sees the commit and rolls the Deployments (§8). CI never needs cluster
  credentials, which is what makes this work with a laptop cluster that GitHub cannot reach.
* GHCR packages are private by default. Make both packages public (package settings → visibility), or give the cluster an `imagePullSecret`.

Every change is a small, conventional commit, so the history doubles as a change log for the pipeline to build from:

<img src="screenshots/33-git-history.png" alt="git log" width="760">

## 6. Security scanning (Trivy)

Each image is scanned twice:
1. **Full report.** All severities, uploaded as SARIF to *Security → Code scanning*.
2. **Gate.** `--severity HIGH,CRITICAL --ignore-unfixed --exit-code 1` fails the job before anything is pushed.

What the gate caught while building this project: the first backend image had **4 HIGH CVEs**.
* `urllib3` CVE-2026-97687 and CVE-2026-97689
* `msgpack` GHSA-6v7p-g79w-8964
* `setuptools` CVE-2025-47273

None of them came from GearLoop's own dependencies. They were copies **vendored inside pip itself**, in the base image and in the venv.
The app never runs pip, so the fix was to uninstall pip/setuptools/wheel from the runtime image instead of suppressing the findings. Both images now scan clean.

<img src="screenshots/21-trivy-scan.png" alt="Trivy scan results">

## 7. Terraform: the cluster's setup as code (`terraform/`)

AWS is out of scope for this project, so Terraform targets the **local Kubernetes cluster** (minikube) through the
official `kubernetes` and `helm` providers. That keeps Infrastructure as Code real: everything below was planned,
applied, destroyed and applied again on this machine.

| File | Manages |
|---|---|
| `namespace.tf` | `gearloop` namespace with Pod Security `restricted` labels, `ResourceQuota`, `LimitRange` |
| `monitoring.tf` | `monitoring` namespace + `kube-prometheus-stack` release (chart version pinned) |
| `app.tf` | the `gearloop` Helm release from `../helm/gearloop`: image repo/tag, pull policy, ingress host, monitoring toggles; `atomic` so a failed rollout rolls back |
| `argocd.tf` | only in `deploy_mode = "argocd"`: `argocd` namespace, Argo CD release, the DB Secret (random password) and the GearLoop `Application` (§8) |
| `variables.tf` · `outputs.tf` | deploy mode, kube context, images, values file, quota, GitOps repo/revision; outputs app/Grafana URLs and the release revision |

```bash
./scripts/minikube-up.sh                  # starts minikube, builds images, then terraform init + apply
# or step by step:
cd terraform
terraform init
terraform plan -out=tf.plan               # 6 to add
terraform apply tf.plan                   # ~40 s on minikube
terraform destroy                         # removes releases, namespaces and the Postgres volume
```

Terraform owns the namespaces, so `destroy` also removes what Helm deliberately keeps on uninstall (the DB Secret and the
Postgres PVC). The first version let Helm create the `monitoring` namespace, and `destroy` left it behind. It is now a
Terraform resource too.

| `terraform plan` | `terraform apply` |
|---|---|
| <img src="screenshots/22a-terraform-plan.png" alt="terraform init, validate and plan"> | <img src="screenshots/22b-terraform-apply.png" alt="terraform apply"> |

<img src="screenshots/22c-terraform-destroy.png" alt="terraform destroy leaves no releases, namespaces or volumes" width="640">

Use **either** Terraform **or** the manual `kubectl apply -f k8s/` + `helm upgrade --install` path below on a given cluster.
Terraform expects to create the namespace itself.

## 8. GitOps with Argo CD (`gitops/`, `terraform/argocd.tf`)

Terraform has two deploy modes:

| `deploy_mode` | Who deploys the GearLoop chart |
|---|---|
| `helm` (default) | Terraform installs the release directly. Works with no Git remote. |
| `argocd` | Terraform installs **Argo CD** and one `Application`; Argo CD deploys `helm/gearloop` from GitHub with `values-gitops.yaml`, and keeps it in sync |

```bash
# after the repo is on GitHub and CI has pushed the first images (packages public):
cd terraform
terraform destroy                                   # switching modes: the DB Secret and volume differ
terraform apply -var deploy_mode=argocd
kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath='{.data.password}' | base64 -d
# UI: http://argocd.gearloop.local  (user admin)
```

Sync policy is **automated with prune and self-heal**: a commit to Git changes the cluster, a resource deleted from Git is
deleted from the cluster, and a manual `kubectl` change is reverted. The database password never goes into Git:
Argo CD renders charts without cluster access (so the chart's generated password would change on every sync), so in this
mode Terraform creates the `gearloop-db` Secret with a random password and the chart uses it via `postgres.existingSecret`.

**Tested locally before the GitHub push.** The same Application was pointed at a throwaway Git server on this machine
(smart HTTP via `git http-backend`), using the locally built images:

1. `terraform apply` in `argocd` mode: 10 resources; the first sync was *Synced / Healthy* in about 95 s.
2. A commit that set the frontend to 3 replicas was pushed to that repo. Argo CD synced it on its own in 18 s.
3. `kubectl scale deploy gearloop-frontend --replicas=1` was reverted to 3 by self-heal in 2 s.
4. `terraform destroy` removed everything, including the Application (its finalizer cleaned up the app first).

<img src="screenshots/38-terraform-argocd-mode.png" alt="terraform apply in argocd mode" width="760">

| Argo CD: application Synced / Healthy | Resource tree |
|---|---|
| <img src="screenshots/35-argocd-applications.png" alt="Argo CD applications view"> | <img src="screenshots/36-argocd-app-tree.png" alt="Argo CD resource tree"> |

| Sync history: two Git revisions | Push → sync → self-heal |
|---|---|
| <img src="screenshots/37-argocd-history.png" alt="Argo CD sync history"> | <img src="screenshots/39-gitops-sync-selfheal.png" alt="GitOps sync and self-heal timings"> |

*These screenshots show the local test repository URL; once the repo is pushed, the Application tracks
`https://github.com/aastik-gg/gearloop.git`.*

## 9. Kubernetes + Helm (`helm/gearloop/`)

```bash
kubectl apply -f k8s/                                         # namespace (PSA restricted) + quota
helm upgrade --install gearloop ./helm/gearloop -n gearloop -f helm/gearloop/values-local.yaml
helm test gearloop -n gearloop
kubectl get pods,svc,ingress,hpa,pdb -n gearloop
```

What the chart renders:

| Object | Notes |
|---|---|
| `Deployment` backend / frontend | ≥2 replicas, rolling updates with `maxUnavailable: 0`, topology spread, startup + readiness + liveness probes, read-only root FS, all capabilities dropped |
| `Service` ×3 | ClusterIP for backend (8000) and frontend (80), headless for Postgres |
| `StatefulSet` postgres | `volumeClaimTemplates` PVC, runs as uid 70; password generated once and kept across upgrades (`lookup`) |
| initContainer `migrate` | in every backend pod: waits for the DB, takes a Postgres advisory lock, runs Alembic to head, seeds an empty DB. The first pod does the work; the others find the schema at head and start |
| `Ingress` | `/api`, `/docs`, `/openapi.json` → backend; `/` → frontend; host `gearloop.local` |
| `HorizontalPodAutoscaler` | backend 2→6 at 60 % CPU, fast scale-up, 2-minute scale-down stabilisation |
| `PodDisruptionBudget` ×2 | keep ≥1 pod during node drains |
| `NetworkPolicy` | only pods labelled `gearloop.io/db-client=true` (the backend) may open 5432 |
| `ServiceMonitor` · `PrometheusRule` · dashboard `ConfigMap` | monitoring (when enabled) |

This is the manual path (Terraform in §7 and Argo CD in §8 do the same thing declaratively). Changing the image tag and running
`helm upgrade` again does a rolling update. `helm rollback gearloop <rev> -n gearloop` goes back to an earlier release.

<img src="screenshots/23-kubectl-resources.png" alt="kubectl get pods,svc,ingress,hpa,pdb">

<img src="screenshots/24-helm-release.png" alt="helm list, history and test">

### One-command local environment (minikube)

```bash
./scripts/minikube-up.sh                  # minikube + addons + images + terraform apply + helm test
echo "$(minikube ip) gearloop.local grafana.gearloop.local" | sudo tee -a /etc/hosts
```

### Why an initContainer and not a Helm hook Job

The first version ran migrations in a `post-install` Helm hook Job. The first real `helm install --wait` on minikube
**deadlocked**:
* Helm waits for every pod to be Ready *before* it runs post-install hooks.
* The backend's `/ready` returns 503 until the tables exist.
* So the pods waited for the migration, and the migration waited for the pods.

Moving the migration into the pod (an initContainer) removes the dependency on Helm's ordering. The advisory lock in
`app/migrate.py` makes it safe with any number of replicas. That was tested with 4 concurrent runs against Postgres:
1 migrated and seeded, and 3 waited and skipped.

## 10. Ingress

The Ingress resource is only configuration. The **ingress-nginx controller** (here the minikube addon)
does the routing. The browser only ever talks to one origin, so there is no CORS and no backend hostname in the JS bundle.

<img src="screenshots/34-app-via-ingress.png" alt="GearLoop served through the Ingress at gearloop.local">

<img src="screenshots/25-ingress-routing.png" alt="Ingress routing rules and curl checks">

The frontend's nginx resolves the backend Service **per request** (`resolver` + variable `proxy_pass`), using the Service FQDN.
Without that, a node restart made nginx exit with `host not found in upstream` before CoreDNS was ready, and the
frontend crash-looped until DNS came back.

## 11. HPA

```bash
./scripts/load-test.sh                         # in-cluster busybox workers hammering /api
watch kubectl get hpa,pods -n gearloop
```

The HPA needs CPU **requests** on the pods (set in `values.yaml`) and a metrics source
(here the minikube `metrics-server` addon).

A real run on the Terraform-managed deployment: CPU jumped to 438 % of the request, and the HPA went 2 → 4 → 6 replicas within about 45 seconds.

<img src="screenshots/26-hpa-autoscaling.png" alt="HPA scaling from 2 to 6 replicas">

<img src="screenshots/30-prometheus-query.png" alt="Requests per second per pod during the load test">

*Requests/s per backend pod: two pods take the first burst, then traffic spreads across the new replicas (Prometheus shows UTC).*

## 12. Monitoring

Terraform installs this (`terraform/monitoring.tf`, same values file). The manual equivalent:

```bash
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm upgrade --install monitoring prometheus-community/kube-prometheus-stack \
  -n monitoring --create-namespace -f monitoring/kube-prometheus-stack-values.yaml
```

* **Prometheus.** The chart's `ServiceMonitor` scrapes backend `/metrics` every 15s. Check *Status → Targets*.
* **Grafana.** The dashboard *GearLoop - Lab Equipment Desk* is auto-imported. Panels: equipment by status, pods up, error rate,
  requests/s by endpoint, p50/p95/p99 latency, status classes, checkouts in the last 24h by category, CPU per pod (the HPA input).
* **Alerts.** Rules for backend down, 5xx rate > 5 %, p95 > 500 ms, and overdue equipment.

<img src="screenshots/27-grafana-dashboard.png" alt="Grafana dashboard">

| Prometheus targets: all 6 backend pods `UP` | The 4 GearLoop alert rules (the overdue-equipment alert is *pending*) |
|---|---|
| <img src="screenshots/28-prometheus-targets.png" alt="Prometheus targets"> | <img src="screenshots/29-prometheus-alerts.png" alt="Prometheus alerts"> |

<img src="screenshots/31-metrics-endpoint.png" alt="Backend /metrics output">

## 13. Troubleshooting lab

[`troubleshooting/README.md`](troubleshooting/README.md) has five broken scenarios, each with symptom, diagnosis and fix:
ImagePullBackOff, Service with no endpoints, Running-but-not-Ready (bad DB secret), OOMKilled (exit 137),
and Ingress pointing at the wrong Service port.

<img src="screenshots/32-troubleshooting-lab.png" alt="Troubleshooting scenarios and their symptoms">

## 14. What has actually been verified

| Area | Status |
|---|---|
| Resilience | ✅ after a minikube node restart the frontend crash-looped (`host not found in upstream`); fixed so nginx resolves per request, verified with an unresolvable upstream (nginx stays up, `/api` → 502) |
| App, tests, migrations | ✅ 21 pytest + 5 vitest pass; `ruff` clean; migrations + `alembic check` run against PostgreSQL 17 |
| UI | ✅ every dialog clicked through in headless Chrome against the real stack (add, check out, return, edit, duplicate-tag error, delete, filters); no horizontal scroll at 390px |
| Docker | ✅ `docker compose up --build` brings up all 4 services; both images run non-root |
| Trivy | ✅ both images clean for fixable HIGH/CRITICAL with Trivy 0.76 (after removing pip, see §6) |
| Helm on minikube | ✅ installed by Terraform (earlier also by hand: install, 4 upgrades, rolling restart of 6 pods); `helm test` passes; Pod Security `restricted` namespace accepted every pod |
| Ingress | ✅ `/`, `/api`, `/docs` routed through ingress-nginx |
| HPA | ✅ `load-test.sh` scaled the backend 2 → 4 → 6 |
| Prometheus / Grafana | ✅ both backend targets UP, 4 alert rules loaded, dashboard auto-imported with every panel populated |
| Troubleshooting lab | ✅ all 5 manifests produce the documented symptom (ErrImagePull, no endpoints, readiness 503, OOMKilled 137, ingress 503) |
| GitHub Actions | ⚠️ `actionlint` clean; needs a push to GitHub to actually run |
| Terraform | ✅ `plan` / `apply` / `destroy` / `apply` run against minikube; `destroy` leaves no releases, namespaces or volumes |
| Argo CD (GitOps) | ✅ against a local Git server: auto-sync of a pushed commit in 18 s, self-heal in 2 s, clean destroy. ⚠️ Against GitHub only after the push |

## 15. Known issues and limitations

* **No cloud deployment.** AWS is out of scope for this project, so Terraform manages a local minikube cluster instead of
  provisioning a VPC and EKS. The chart and pipeline are cluster-agnostic (`values-prod.yaml`), but they were not run on a cloud provider.
* **CI, GHCR and Argo CD-from-GitHub run only after the push.** The workflow is `actionlint`-clean and every step was run
  locally, but the first green GitHub Actions run, the SHA-tagged GHCR packages and the GitHub-backed Argo CD sync happen once the repository is on GitHub.
* **`values-gitops.yaml` starts with the tag `bootstrap`.** Until the first CI run on `main` replaces it, Argo CD mode
  shows `ImagePullBackOff`. GHCR packages are private by default; make them public or add an `imagePullSecret`.
* **Single-node demo database.** PostgreSQL runs as one StatefulSet replica on a minikube hostPath volume, with no
  backups or replication. A real deployment would use a managed database (`postgres.enabled=false` + `postgres.externalUrl`).
* **Plain HTTP locally.** Ingress, Grafana and Argo CD are served over HTTP on `*.gearloop.local` hosts that must be added to
  `/etc/hosts`. The chart supports TLS (`ingress.tls`), but no certificates are configured.
* **Demo credentials.** Grafana's admin password is a demo value in `monitoring/kube-prometheus-stack-values.yaml`, and
  `values-local.yaml` uses a fixed local DB password. Neither is used in Argo CD mode for the database, but change both for anything shared.
* **CRDs survive `terraform destroy`.** Helm intentionally leaves the Prometheus Operator and Argo CD CRDs installed.
  Everything else (namespaces, releases, Secrets, volumes) is removed.
* **One transient delete error.** During the first mode switch, `terraform destroy` once reported a Kubernetes delete
  error. Running it again finished cleanly, and the error did not recur in any later run.
* **Seeded demo data.** An empty database is seeded with 10 items and 3 loans on first start (`--seed`). Turn this off with
  `migrations.seedDemoData=false`.

## 16. Video walkthrough order

The walkthrough video follows the order the rubric asks for. The step-by-step script with the exact commands is
[`demo/RECORDING-GUIDE.md`](demo/RECORDING-GUIDE.md).

1. Slides: what GearLoop is, tech stack, architecture.
2. Codebase: folder structure, key files.
3. CI/CD: push a change and show the GitHub Actions run go green end to end (tests → images → Trivy → GHCR → gitops commit).
4. Terraform: `terraform plan` and `apply` against minikube (and the note that AWS is out of scope).
5. Argo CD: the synced application, then the GitOps flow (the CI commit gets deployed, and self-heal reverts a manual change).
6. Kubernetes: `kubectl get pods,svc,ingress,hpa`, and the app through the Ingress.
7. Prometheus: Targets page with the app `UP`.
8. Grafana: the live GearLoop dashboard (run `scripts/load-test.sh` for traffic and HPA scaling).
