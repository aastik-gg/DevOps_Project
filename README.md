# GearLoop: Lab Equipment Desk

GearLoop tracks shared lab equipment: oscilloscopes, cameras, dev kits, tools.
Staff register items. Students check them out for a set number of days and return them.
The desk sees what is available, what is on loan, what is **overdue**, and what is waiting for repair.

This repository is my **Session 21 DevOps capstone**. It takes the app from a laptop
to a monitored Kubernetes deployment:

> React + Vite → FastAPI → PostgreSQL (SQLAlchemy + Alembic) → pytest → Docker → GitHub Actions →
> Trivy → GHCR → Terraform → Helm → Kubernetes (minikube) → Ingress → HPA → Prometheus + Grafana → troubleshooting

The DevOps layer follows the course architecture. The application domain, the code and these design choices are my own.

![GearLoop dashboard](screenshots/01-dashboard.png)

*All screenshots in this README were captured from the running app and cluster; the full set is in [`screenshots/`](screenshots).*

**Presentation:** [`presentation/GearLoop-Capstone.pptx`](presentation/GearLoop-Capstone.pptx), 19 slides with speaker notes.

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
| Terraform | AWS VPC + EKS modules | no cloud account needed: Terraform owns the **local cluster's** namespaces, quota and both Helm releases (monitoring + app), so `plan` / `apply` / `destroy` actually run, and `destroy` leaves nothing behind |

---

## Architecture

```text
 Developer ── git push ──► GitHub ──► GitHub Actions
                                       ├─ backend : ruff · alembic upgrade/check on Postgres · pytest
                                       ├─ frontend: vitest · vite build
                                       ├─ infra   : helm lint/template · terraform fmt/validate
                                       └─ images (matrix: backend, frontend)
                                            build ─► Trivy (SARIF + HIGH/CRITICAL gate) ─► push ghcr.io/…:<commit-sha>
                                                                                              │
   Terraform (kubernetes + helm providers): namespaces, quota, kube-prometheus-stack, gearloop  │ helm upgrade --install
                                                   │                                          ▼
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
├── terraform/                namespace.tf · monitoring.tf · app.tf · variables.tf · outputs.tf · terraform.tfvars.example
├── helm/gearloop/            chart + values-local.yaml (minikube) + values-prod.yaml (GHCR images) + dashboards/gearloop.json
├── k8s/                      namespace (Pod Security restricted) + ResourceQuota/LimitRange
├── monitoring/               kube-prometheus-stack values
├── troubleshooting/          5 broken manifests + guided README
└── scripts/                  minikube-up.sh · load-test.sh
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
frontend ├─► images [backend, frontend] ─► deploy (main only, opt-in)
infra ───┘     build → Trivy SARIF → Trivy gate → push :<sha>
```

* Runs on every push and PR to `main`. Images are **pushed only from `main`**, tagged with the full commit SHA (never `latest`).
* Every action is pinned to a commit SHA, so a hijacked tag cannot change what runs.
* Deploy needs two things in the repo settings once the cluster exists:
  * variable `DEPLOY_ENABLED=true`
  * secret `KUBE_CONFIG_DATA` = `base64 -w0 ~/.kube/config`

  It then runs `helm upgrade --install --atomic --wait` and `helm test`. Without those settings the job is skipped and the pipeline stays green.
* GHCR packages are private by default. Make them public, or give the cluster an `imagePullSecret`.

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
| `variables.tf` · `outputs.tf` | kube context, images, values file, quota; outputs app/Grafana URLs and the release revision |

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

## 8. Kubernetes + Helm (`helm/gearloop/`)

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

This is the manual path (Terraform in §7 does the same thing declaratively). Changing the image tag and running
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

## 9. Ingress

The Ingress resource is only configuration. The **ingress-nginx controller** (here the minikube addon)
does the routing. The browser only ever talks to one origin, so there is no CORS and no backend hostname in the JS bundle.

<img src="screenshots/34-app-via-ingress.png" alt="GearLoop served through the Ingress at gearloop.local">

<img src="screenshots/25-ingress-routing.png" alt="Ingress routing rules and curl checks">

The frontend's nginx resolves the backend Service **per request** (`resolver` + variable `proxy_pass`), using the Service FQDN.
Without that, a node restart made nginx exit with `host not found in upstream` before CoreDNS was ready, and the
frontend crash-looped until DNS came back.

## 10. HPA

```bash
./scripts/load-test.sh                         # in-cluster busybox workers hammering /api
watch kubectl get hpa,pods -n gearloop
```

The HPA needs CPU **requests** on the pods (set in `values.yaml`) and a metrics source
(here the minikube `metrics-server` addon).

A real run on minikube: CPU jumped to 363 % of the request, and the HPA went 2 → 4 → 6 replicas within about 45 seconds.

<img src="screenshots/26-hpa-autoscaling.png" alt="HPA scaling from 2 to 6 replicas">

<img src="screenshots/30-prometheus-query.png" alt="Requests per second per pod during the load test">

*Requests/s per backend pod: two pods take the first burst, then traffic spreads across the new replicas (Prometheus shows UTC).*

## 11. Monitoring

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

| Prometheus targets: every backend pod `UP` | Alert rules (the load test pushed p95 over 500 ms → *pending*) |
|---|---|
| <img src="screenshots/28-prometheus-targets.png" alt="Prometheus targets"> | <img src="screenshots/29-prometheus-alerts.png" alt="Prometheus alerts"> |

<img src="screenshots/31-metrics-endpoint.png" alt="Backend /metrics output">

## 12. Troubleshooting lab

[`troubleshooting/README.md`](troubleshooting/README.md) has five broken scenarios, each with symptom, diagnosis and fix:
ImagePullBackOff, Service with no endpoints, Running-but-not-Ready (bad DB secret), OOMKilled (exit 137),
and Ingress pointing at the wrong Service port.

<img src="screenshots/32-troubleshooting-lab.png" alt="Troubleshooting scenarios and their symptoms">

## 13. What has actually been verified

| Area | Status |
|---|---|
| Resilience | ✅ after a minikube node restart the frontend crash-looped (`host not found in upstream`); fixed so nginx resolves per request, verified with an unresolvable upstream (nginx stays up, `/api` → 502) |
| App, tests, migrations | ✅ 21 pytest + 5 vitest pass; `ruff` clean; migrations + `alembic check` run against PostgreSQL 17 |
| UI | ✅ every dialog clicked through in headless Chrome against the real stack (add, check out, return, edit, duplicate-tag error, delete, filters); no horizontal scroll at 390px |
| Docker | ✅ `docker compose up --build` brings up all 4 services; both images run non-root |
| Trivy | ✅ both images clean for fixable HIGH/CRITICAL with Trivy 0.76 (after removing pip, see §6) |
| Helm on minikube | ✅ install, 3 upgrades, rolling restart of 6 pods, `helm test` passes; Pod Security `restricted` namespace accepted every pod |
| Ingress | ✅ `/`, `/api`, `/docs` routed through ingress-nginx |
| HPA | ✅ `load-test.sh` scaled the backend 2 → 4 → 6 |
| Prometheus / Grafana | ✅ both backend targets UP, 4 alert rules loaded, dashboard auto-imported with every panel populated |
| Troubleshooting lab | ✅ all 5 manifests produce the documented symptom (ErrImagePull, no endpoints, readiness 503, OOMKilled 137, ingress 503) |
| GitHub Actions | ⚠️ `actionlint` clean; needs a push to GitHub to actually run |
| Terraform | ✅ `plan` / `apply` / `destroy` / `apply` run against minikube; `destroy` leaves no releases, namespaces or volumes |

## 14. Final demo script

1. Open the app, check out an item, watch the summary strip and activity feed update.
2. Use `/docs` to do item CRUD; `kubectl exec -it gearloop-postgres-0 -n gearloop -- psql -U gearloop -c 'select * from loans'`.
3. Change something visible, `git commit`, `git push`; watch CI go backend/frontend/infra → images → deploy.
4. Show the SHA-tagged images in GHCR and the Trivy results in the Security tab.
5. `terraform plan` / `apply`: Terraform creates the namespaces, quota and both Helm releases.
6. `kubectl get pods,svc,ingress,hpa -n gearloop`, `helm list -n gearloop`, `helm history gearloop -n gearloop`.
7. Run `load-test.sh` and watch the HPA scale; show the Grafana dashboard live.
8. Apply a troubleshooting manifest and fix it live.
9. `terraform destroy`, then `kubectl get ns,pv` to show nothing is left.
