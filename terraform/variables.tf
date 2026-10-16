variable "aws_region" {
  description = "AWS region for every resource"
  type        = string
  default     = "ap-south-1"
}

variable "environment" {
  description = "Environment name used in resource names and tags"
  type        = string
  default     = "dev"
}

variable "cluster_name" {
  description = "EKS cluster name"
  type        = string
  default     = "gearloop-eks"
}

variable "kubernetes_version" {
  description = "EKS control plane version"
  type        = string
  default     = "1.34"
}

variable "vpc_cidr" {
  description = "CIDR block for the VPC"
  type        = string
  default     = "10.42.0.0/16"
}

variable "az_count" {
  description = "How many availability zones to spread subnets over (EKS needs at least 2)"
  type        = number
  default     = 2

  validation {
    condition     = var.az_count >= 2 && var.az_count <= 3
    error_message = "az_count must be 2 or 3."
  }
}

variable "use_nat_gateway" {
  description = <<-EOT
    true  = worker nodes live in private subnets behind one NAT gateway (closer to production).
    false = nodes go in the public subnets with public IPs; cheaper for a short classroom demo.
  EOT
  type        = bool
  default     = true
}

variable "node_instance_types" {
  description = "EC2 instance types for the managed node group"
  type        = list(string)
  default     = ["t3.medium"]
}

variable "node_capacity_type" {
  description = "ON_DEMAND or SPOT"
  type        = string
  default     = "ON_DEMAND"
}

variable "node_min_size" {
  type    = number
  default = 2
}

variable "node_desired_size" {
  type    = number
  default = 2
}

variable "node_max_size" {
  type    = number
  default = 4
}

variable "cluster_public_access_cidrs" {
  description = "Who may reach the Kubernetes API endpoint. Narrow this to your own IP."
  type        = list(string)
  default     = ["0.0.0.0/0"]
}
