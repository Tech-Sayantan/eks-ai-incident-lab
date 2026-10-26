locals {
  github_subject = "repo:Tech-Sayantan@298946378/eks-ai-incident-lab@${var.github_repo_id}:ref:refs/heads/main"
}

resource "aws_iam_openid_connect_provider" "github" {
  url            = "https://token.actions.githubusercontent.com"
  client_id_list = ["sts.amazonaws.com"]

  tags = {
    Purpose = "GitHubOIDC"
  }
}

resource "aws_iam_role" "github_identity_smoke" {
  name        = "eks-ai-incident-lab-gha-identity"
  description = "Proves GitHub Actions OIDC federation; no AWS resource permissions yet."

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
    Purpose = "GitHubOIDCSmoke"
  }
}

output "github_oidc_role_arn" {
  value = aws_iam_role.github_identity_smoke.arn
}