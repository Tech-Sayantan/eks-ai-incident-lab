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
  orders_domain   = "orders.tanscape.online"
  certificate_dns = one(aws_acm_certificate.orders.domain_validation_options)
}

resource "aws_route53_zone" "orders" {
  name    = local.orders_domain
  comment = "orders.tanscape.online POC"
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

resource "aws_route53_record" "certificate_validation" {
  zone_id = aws_route53_zone.orders.zone_id
  name    = local.certificate_dns.resource_record_name
  type    = local.certificate_dns.resource_record_type
  ttl     = 300
  records = [local.certificate_dns.resource_record_value]
}

resource "aws_route53_record" "orders_alias" {
  zone_id = aws_route53_zone.orders.zone_id
  name    = local.orders_domain
  type    = "A"

  # The AWS Load Balancer Controller owns this ALB.
  alias {
    name                   = "k8s-ordersla-ordersap-613c362ac3-2141733110.ap-south-1.elb.amazonaws.com"
    zone_id                = "ZP97RAFLXTNZK"
    evaluate_target_health = true
  }
}
