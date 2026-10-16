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
