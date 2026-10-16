# The namespace is owned by Terraform, so `terraform destroy` also removes what Helm
# deliberately leaves behind (the kept DB Secret and the Postgres PVC).
resource "kubernetes_namespace_v1" "gearloop" {
  metadata {
    name = var.namespace
    labels = {
      "app.kubernetes.io/part-of" = "gearloop"
      # Pod Security Admission: reject pods that run as root, escalate privileges, etc.
      "pod-security.kubernetes.io/enforce"         = "restricted"
      "pod-security.kubernetes.io/enforce-version" = "latest"
      "pod-security.kubernetes.io/warn"            = "restricted"
    }
  }
}

resource "kubernetes_resource_quota_v1" "gearloop" {
  metadata {
    name      = "gearloop-quota"
    namespace = kubernetes_namespace_v1.gearloop.metadata[0].name
  }
  spec {
    hard = {
      "requests.cpu"           = var.quota.requests_cpu
      "requests.memory"        = var.quota.requests_memory
      "limits.cpu"             = var.quota.limits_cpu
      "limits.memory"          = var.quota.limits_memory
      "persistentvolumeclaims" = "4"
      "pods"                   = tostring(var.quota.pods)
    }
  }
}

resource "kubernetes_limit_range_v1" "gearloop" {
  metadata {
    name      = "gearloop-defaults"
    namespace = kubernetes_namespace_v1.gearloop.metadata[0].name
  }
  spec {
    limit {
      type            = "Container"
      default         = { cpu = "250m", memory = "256Mi" }
      default_request = { cpu = "50m", memory = "64Mi" }
    }
  }
}
