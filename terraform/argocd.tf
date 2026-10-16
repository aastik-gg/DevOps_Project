# deploy_mode = "argocd": Terraform installs Argo CD and one Application; from then on
# Argo CD keeps the cluster in sync with Git (CI bumps image tags in values-gitops.yaml).

resource "kubernetes_namespace_v1" "argocd" {
  count = var.deploy_mode == "argocd" ? 1 : 0

  metadata {
    name   = "argocd"
    labels = { "app.kubernetes.io/part-of" = "gearloop" }
  }
}

resource "helm_release" "argocd" {
  count = var.deploy_mode == "argocd" ? 1 : 0

  name       = "argocd"
  repository = "https://argoproj.github.io/argo-helm"
  chart      = "argo-cd"
  version    = var.argocd_chart_version
  namespace  = kubernetes_namespace_v1.argocd[0].metadata[0].name

  values = [file("${path.module}/../gitops/argocd-values.yaml")]

  set = [{ name = "server.ingress.hostname", value = "argocd.${var.ingress_host}" }]

  wait    = true
  timeout = 600
}

# The DB credentials live only in the cluster (and Terraform state), never in Git.
resource "random_password" "db" {
  count = var.deploy_mode == "argocd" ? 1 : 0

  length  = 24
  special = false
}

resource "kubernetes_secret_v1" "db" {
  count = var.deploy_mode == "argocd" ? 1 : 0

  metadata {
    name      = "gearloop-db"
    namespace = kubernetes_namespace_v1.gearloop.metadata[0].name
  }
  data = {
    username     = "gearloop"
    password     = random_password.db[0].result
    database-url = "postgresql+psycopg://gearloop:${random_password.db[0].result}@gearloop-postgres:5432/gearloop"
  }
}

resource "helm_release" "argocd_apps" {
  count = var.deploy_mode == "argocd" ? 1 : 0

  name       = "argocd-apps"
  repository = "https://argoproj.github.io/argo-helm"
  chart      = "argocd-apps"
  version    = var.argocd_apps_chart_version
  namespace  = kubernetes_namespace_v1.argocd[0].metadata[0].name

  values = [yamlencode({
    applications = {
      gearloop = {
        namespace  = "argocd"
        finalizers = ["resources-finalizer.argocd.argoproj.io"]
        project    = "default"
        source = {
          repoURL        = var.gitops_repo_url
          targetRevision = var.gitops_revision
          path           = "helm/gearloop"
          helm = {
            valueFiles = var.gitops_value_files
            # Always use the Terraform-created Secret, whatever the values files say.
            parameters = [{ name = "postgres.existingSecret", value = "gearloop-db" }]
          }
        }
        destination = {
          server    = "https://kubernetes.default.svc"
          namespace = kubernetes_namespace_v1.gearloop.metadata[0].name
        }
        syncPolicy = {
          automated = { prune = true, selfHeal = true }
        }
      }
    }
  })]

  depends_on = [
    helm_release.argocd,
    helm_release.monitoring,
    kubernetes_secret_v1.db,
    kubernetes_resource_quota_v1.gearloop,
    kubernetes_limit_range_v1.gearloop,
  ]
}
