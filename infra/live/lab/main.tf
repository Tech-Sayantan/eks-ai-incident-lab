terraform {
  required_version = "~> 1.15.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.0"
    }
  }
}

variable "expected_account_id" {
  description = "AWS account ID that is allowed to receive lab resources."
  type        = string
}

variable "operator_cidr" {
  description = "Your current public IPv4 address as a /32 CIDR for EKS API access."
  type        = string

  validation {
    condition     = can(cidrnetmask(var.operator_cidr)) && endswith(var.operator_cidr, "/32")
    error_message = "operator_cidr must be one valid IPv4 address ending in /32."
  }
}

provider "aws" {
  region              = "ap-south-1"
  allowed_account_ids = [var.expected_account_id]

  default_tags {
    tags = {
      Project   = "eks-ai-incident-lab"
      ManagedBy = "Terraform"
    }
  }
}

data "aws_availability_zones" "available" {
  state = "available"
}

module "network" {
  source = "../../modules/network"

  name                = "eks-ai-incident-lab"
  vpc_cidr            = "10.42.0.0/16"
  availability_zones  = slice(sort(data.aws_availability_zones.available.names), 0, 2)
  public_subnet_cidrs = ["10.42.0.0/24", "10.42.1.0/24"]
}

module "eks" {
  source = "../../modules/eks"

  name               = "eks-ai-incident-lab"
  kubernetes_version = "1.36"
  public_subnet_ids  = module.network.public_subnet_ids
  operator_cidr      = var.operator_cidr
  operator_arn       = "arn:aws:iam::${var.expected_account_id}:user/eks-lab-admin"
}

output "vpc_id" {
  value = module.network.vpc_id
}

output "public_subnet_ids" {
  value = module.network.public_subnet_ids
}

output "cluster_name" {
  value = module.eks.cluster_name
}
