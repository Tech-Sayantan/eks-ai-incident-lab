resource "aws_ecr_repository" "investigator" {
  name                 = "${local.cluster_name}/orders-investigator"
  image_tag_mutability = "IMMUTABLE"

  encryption_configuration {
    encryption_type = "AES256"
  }

  image_scanning_configuration {
    scan_on_push = true
  }
}

data "aws_iam_role" "github_image_publisher" {
  name = "${local.cluster_name}-gha-image-publish"
}

resource "aws_iam_role_policy" "github_image_publisher" {
  name = "publish-orders-investigator-image"
  role = data.aws_iam_role.github_image_publisher.name

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Action = [
        "ecr:BatchCheckLayerAvailability",
        "ecr:BatchGetImage",
        "ecr:CompleteLayerUpload",
        "ecr:DescribeImages",
        "ecr:InitiateLayerUpload",
        "ecr:PutImage",
        "ecr:UploadLayerPart"
      ]
      Resource = aws_ecr_repository.investigator.arn
    }]
  })
}

output "ecr_repository_url" {
  description = "Private investigator container repository URL."
  value       = aws_ecr_repository.investigator.repository_url
}
