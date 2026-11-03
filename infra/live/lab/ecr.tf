locals {
  app_image_names = toset(["orders-api", "payment-simulator"])
}

resource "aws_ecr_repository" "app" {
  for_each = local.app_image_names

  name                 = "eks-ai-incident-lab/${each.key}"
  image_tag_mutability = "IMMUTABLE"
  force_delete         = true

  encryption_configuration {
    encryption_type = "AES256"
  }

  image_scanning_configuration {
    scan_on_push = true
  }
}

output "ecr_repository_urls" {
  description = "Private image repository URLs for the two applications."
  value = {
    for name, repo in aws_ecr_repository.app :
    name => repo.repository_url
  }
}
