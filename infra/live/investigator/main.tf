terraform {
  required_version = "~> 1.15.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.0"
    }
  }
}

locals {
  region          = "ap-south-1"
  account_id      = "923988301700"
  cluster_name    = "eks-ai-incident-lab"
  namespace       = "orders-lab"
  service_account = "orders-investigator"
  mantle_model    = "openai.gpt-oss-20b"
}

provider "aws" {
  region              = local.region
  allowed_account_ids = [local.account_id]

  default_tags {
    tags = {
      Project   = "eks-ai-incident-lab"
      Component = "orders-investigator"
      ManagedBy = "Terraform"
    }
  }
}

data "aws_eks_cluster" "lab" {
  name = local.cluster_name
}

data "aws_eks_addon_version" "pod_identity" {
  addon_name         = "eks-pod-identity-agent"
  kubernetes_version = data.aws_eks_cluster.lab.version
}

resource "aws_eks_addon" "pod_identity" {
  cluster_name  = data.aws_eks_cluster.lab.name
  addon_name    = data.aws_eks_addon_version.pod_identity.addon_name
  addon_version = data.aws_eks_addon_version.pod_identity.version
}

resource "aws_iam_role" "investigator" {
  name        = "${local.cluster_name}-orders-investigator"
  description = "Pod Identity role for the Orders investigator"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Principal = {
        Service = "pods.eks.amazonaws.com"
      }
      Action = ["sts:AssumeRole", "sts:TagSession"]
      Condition = {
        StringEquals = {
          "aws:RequestTag/eks-cluster-arn"            = data.aws_eks_cluster.lab.arn
          "aws:RequestTag/kubernetes-namespace"       = local.namespace
          "aws:RequestTag/kubernetes-service-account" = local.service_account
        }
      }
    }]
  })
}

resource "aws_iam_role_policy" "mantle" {
  name = "invoke-lab-mantle-model"
  role = aws_iam_role.investigator.name

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = "bedrock-mantle:CreateInference"
      Resource = "arn:aws:bedrock-mantle:${local.region}:${local.account_id}:project/default"
      Condition = {
        StringEquals = {
          "bedrock-mantle:Model" = local.mantle_model
        }
      }
    }]
  })
}

resource "aws_eks_pod_identity_association" "investigator" {
  cluster_name    = data.aws_eks_cluster.lab.name
  namespace       = local.namespace
  service_account = local.service_account
  role_arn        = aws_iam_role.investigator.arn

  depends_on = [aws_eks_addon.pod_identity, aws_iam_role_policy.mantle]
}

output "pod_identity_role_arn" {
  description = "AWS role assumed by the orders-investigator service account."
  value       = aws_iam_role.investigator.arn
}
