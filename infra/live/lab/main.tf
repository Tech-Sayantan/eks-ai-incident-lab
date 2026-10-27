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

output "vpc_id" {
  value = module.network.vpc_id
}

output "public_subnet_ids" {
  value = module.network.public_subnet_ids
}