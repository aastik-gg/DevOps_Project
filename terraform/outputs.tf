output "namespace" {
  value = kubernetes_namespace_v1.gearloop.metadata[0].name
}

output "deploy_mode" {
  value = var.deploy_mode
}

output "release" {
  value = var.deploy_mode == "helm" ? "${helm_release.gearloop[0].name} rev ${helm_release.gearloop[0].metadata.revision} (${helm_release.gearloop[0].status})" : "managed by Argo CD from ${var.gitops_repo_url} (${var.gitops_revision})"
}

output "argocd_url" {
  value = var.deploy_mode == "argocd" ? "http://argocd.${var.ingress_host}/  (user admin; password: kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath='{.data.password}' | base64 -d)" : null
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
