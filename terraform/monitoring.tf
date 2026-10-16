# Owned by Terraform (not Helm's create_namespace) so `terraform destroy` removes it too.
resource "kubernetes_namespace_v1" "monitoring" {
  count = var.enable_monitoring ? 1 : 0

  metadata {
    name   = "monitoring"
    labels = { "app.kubernetes.io/part-of" = "gearloop" }
  }
}

# Prometheus Operator + Prometheus + Grafana + Alertmanager. Installed first because the
# GearLoop chart's ServiceMonitor and PrometheusRule need its CRDs.
resource "helm_release" "monitoring" {
  count = var.enable_monitoring ? 1 : 0

  name       = "monitoring"
  repository = "https://prometheus-community.github.io/helm-charts"
  chart      = "kube-prometheus-stack"
  version    = var.monitoring_chart_version
  namespace  = kubernetes_namespace_v1.monitoring[0].metadata[0].name

  values = [file("${path.module}/../monitoring/kube-prometheus-stack-values.yaml")]

  wait    = true
  timeout = 900
}
