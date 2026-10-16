resource "helm_release" "gearloop" {
  name      = "gearloop"
  chart     = "${path.module}/../helm/gearloop"
  namespace = kubernetes_namespace_v1.gearloop.metadata[0].name

  values = [file("${path.module}/../helm/gearloop/${var.values_file}")]

  set = [
    { name = "backend.image.repository", value = var.backend_image.repository },
    { name = "backend.image.tag", value = var.backend_image.tag },
    { name = "backend.image.pullPolicy", value = var.image_pull_policy },
    { name = "frontend.image.repository", value = var.frontend_image.repository },
    { name = "frontend.image.tag", value = var.frontend_image.tag },
    { name = "frontend.image.pullPolicy", value = var.image_pull_policy },
    { name = "ingress.host", value = var.ingress_host },
    { name = "monitoring.serviceMonitor.enabled", value = tostring(var.enable_monitoring) },
    { name = "monitoring.prometheusRule.enabled", value = tostring(var.enable_monitoring) },
    { name = "monitoring.grafanaDashboard.enabled", value = tostring(var.enable_monitoring) },
  ]

  # Roll back automatically if the pods never become Ready.
  atomic  = true
  wait    = true
  timeout = 600

  depends_on = [
    helm_release.monitoring,
    kubernetes_resource_quota_v1.gearloop,
    kubernetes_limit_range_v1.gearloop,
  ]
}
