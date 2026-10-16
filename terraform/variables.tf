variable "kubeconfig_path" {
  description = "kubeconfig used by the kubernetes and helm providers"
  type        = string
  default     = "~/.kube/config"
}

variable "kube_context" {
  description = "kubeconfig context to deploy into"
  type        = string
  default     = "minikube"
}

variable "deploy_mode" {
  description = <<-EOT
    How the GearLoop chart reaches the cluster:
      helm   = Terraform installs the release directly (works offline, no Git remote needed)
      argocd = Terraform installs Argo CD, which deploys the chart from Git (GitOps)
    Switch modes with `terraform destroy` first: the database volume and Secret differ.
  EOT
  type        = string
  default     = "helm"

  validation {
    condition     = contains(["helm", "argocd"], var.deploy_mode)
    error_message = "deploy_mode must be helm or argocd."
  }
}

variable "namespace" {
  description = "Namespace for the GearLoop release"
  type        = string
  default     = "gearloop"
}

variable "values_file" {
  description = "Chart values file under helm/gearloop/ for this environment"
  type        = string
  default     = "values-local.yaml"
}

variable "backend_image" {
  description = "Backend image repository and tag"
  type        = object({ repository = string, tag = string })
  default     = { repository = "gearloop-backend", tag = "local" }
}

variable "frontend_image" {
  description = "Frontend image repository and tag"
  type        = object({ repository = string, tag = string })
  default     = { repository = "gearloop-frontend", tag = "local" }
}

variable "image_pull_policy" {
  description = "Never for images built inside minikube, IfNotPresent for registry images"
  type        = string
  default     = "Never"

  validation {
    condition     = contains(["Always", "IfNotPresent", "Never"], var.image_pull_policy)
    error_message = "image_pull_policy must be Always, IfNotPresent or Never."
  }
}

variable "ingress_host" {
  description = "Host name the Ingress answers on"
  type        = string
  default     = "gearloop.local"
}

variable "enable_monitoring" {
  description = "Install kube-prometheus-stack and the chart's ServiceMonitor, alert rules and dashboard"
  type        = bool
  default     = true
}

variable "monitoring_chart_version" {
  description = "Pinned kube-prometheus-stack chart version"
  type        = string
  default     = "92.9.0"
}

variable "quota" {
  description = "Upper bound on what the whole namespace may request"
  type = object({
    requests_cpu    = string
    requests_memory = string
    limits_cpu      = string
    limits_memory   = string
    pods            = number
  })
  default = {
    requests_cpu    = "4"
    requests_memory = "4Gi"
    limits_cpu      = "8"
    limits_memory   = "8Gi"
    pods            = 30
  }
}

# ---- GitOps (deploy_mode = "argocd") ----
variable "gitops_repo_url" {
  description = "Git repository Argo CD deploys from"
  type        = string
  default     = "https://github.com/aastik-gg/gearloop.git"
}

variable "gitops_revision" {
  description = "Branch, tag or commit Argo CD tracks"
  type        = string
  default     = "main"
}

variable "gitops_value_files" {
  description = "Values files (relative to helm/gearloop) Argo CD renders the chart with"
  type        = list(string)
  default     = ["values-gitops.yaml"]
}

variable "argocd_chart_version" {
  description = "Pinned argo-cd chart version"
  type        = string
  default     = "10.10.5"
}

variable "argocd_apps_chart_version" {
  description = "Pinned argocd-apps chart version"
  type        = string
  default     = "2.0.6"
}
