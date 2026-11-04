resource "aws_iam_role" "gha_image_publisher" {
  name        = "eks-ai-incident-lab-gha-image-publish"
  description = "GitHub Actions role for publishing the two lab images."

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Principal = {
        Federated = aws_iam_openid_connect_provider.github.arn
      }
      Action = "sts:AssumeRoleWithWebIdentity"
      Condition = {
        StringEquals = {
          "token.actions.githubusercontent.com:aud" = "sts.amazonaws.com"
          "token.actions.githubusercontent.com:sub" = local.github_subject
        }
      }
    }]
  })

  tags = {
    Purpose = "GitHubImagePublisher"
  }
}

resource "aws_iam_role_policy" "gha_image_publisher" {
  name = "lab-image-publish"
  role = aws_iam_role.gha_image_publisher.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid      = "AuthenticateToECR"
        Effect   = "Allow"
        Action   = "ecr:GetAuthorizationToken"
        Resource = "*"
      },
      {
        Sid    = "PublishTwoLabImages"
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
        Resource = local.lab_ecr_repository_arns
      }
    ]
  })
}

output "github_image_publisher_role_arn" {
  value = aws_iam_role.gha_image_publisher.arn
}