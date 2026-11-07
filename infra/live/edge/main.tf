terraform {
  required_version = "~> 1.15.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.0"
    }
  }
}

provider "aws" {
  region              = "ap-south-1"
  allowed_account_ids = ["923988301700"]
}

locals {
  orders_domain = "orders.tanscape.online"
}

resource "aws_acm_certificate" "orders" {
  domain_name       = local.orders_domain
  validation_method = "DNS"
  key_algorithm     = "RSA_2048"

  options {
    certificate_transparency_logging_preference = "ENABLED"
    export                                      = "DISABLED"
  }

  tags = {
    Project = "eks-ai-incident-lab"
  }
}
