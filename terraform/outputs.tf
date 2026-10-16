output "namespace" {
  value = kubernetes_namespace_v1.gearloop.metadata[0].name
}

output "release" {
  value = "${helm_release.gearloop.name} rev ${helm_release.gearloop.metadata.revision} (${helm_release.gearloop.status})"
}

output "app_url" {
  value = "http://${var.ingress_host}/"
}

output "grafana_url" {
  value = var.enable_monitoring ? "http://grafana.${var.ingress_host}/" : null
}

output "next_steps" {
  value = <<-EOT
    echo "$(minikube ip) ${var.ingress_host} grafana.${var.ingress_host}" | sudo tee -a /etc/hosts
    helm test gearloop -n ${var.namespace}
  EOT
}
