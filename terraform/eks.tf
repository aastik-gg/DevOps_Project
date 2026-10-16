resource "aws_eks_cluster" "main" {
  name     = var.cluster_name
  version  = var.kubernetes_version
  role_arn = aws_iam_role.cluster.arn

  access_config {
    authentication_mode                         = "API"
    bootstrap_cluster_creator_admin_permissions = true # whoever runs `terraform apply` gets cluster-admin
  }

  vpc_config {
    subnet_ids              = concat(aws_subnet.public[*].id, aws_subnet.private[*].id)
    endpoint_public_access  = true
    endpoint_private_access = true
    public_access_cidrs     = var.cluster_public_access_cidrs
  }

  enabled_cluster_log_types = ["api", "audit", "authenticator"]

  depends_on = [aws_iam_role_policy_attachment.cluster]
}

resource "aws_eks_node_group" "main" {
  cluster_name    = aws_eks_cluster.main.name
  node_group_name = "${local.name}-default"
  node_role_arn   = aws_iam_role.node.arn
  subnet_ids      = local.node_subnet_ids
  instance_types  = var.node_instance_types
  capacity_type   = var.node_capacity_type
  disk_size       = 30

  scaling_config {
    min_size     = var.node_min_size
    desired_size = var.node_desired_size
    max_size     = var.node_max_size
  }

  update_config {
    max_unavailable = 1
  }

  labels = { workload = "general" }

  # Nodes need IAM permissions, and in NAT mode outbound internet, before they can join.
  depends_on = [
    aws_iam_role_policy_attachment.node,
    aws_route.private_nat,
    aws_route_table_association.public,
  ]

  lifecycle {
    ignore_changes = [scaling_config[0].desired_size] # let the cluster autoscaler / humans resize
  }
}

# ---- Managed add-ons ----
locals {
  addons = ["vpc-cni", "kube-proxy", "coredns", "eks-pod-identity-agent", "metrics-server"]
}

resource "aws_eks_addon" "core" {
  for_each                    = toset(local.addons)
  cluster_name                = aws_eks_cluster.main.name
  addon_name                  = each.value
  resolve_conflicts_on_create = "OVERWRITE"
  resolve_conflicts_on_update = "OVERWRITE"

  depends_on = [aws_eks_node_group.main]
}

resource "aws_eks_addon" "ebs_csi" {
  cluster_name                = aws_eks_cluster.main.name
  addon_name                  = "aws-ebs-csi-driver"
  resolve_conflicts_on_create = "OVERWRITE"
  resolve_conflicts_on_update = "OVERWRITE"

  pod_identity_association {
    role_arn        = aws_iam_role.ebs_csi.arn
    service_account = "ebs-csi-controller-sa"
  }

  depends_on = [aws_eks_addon.core]
}
