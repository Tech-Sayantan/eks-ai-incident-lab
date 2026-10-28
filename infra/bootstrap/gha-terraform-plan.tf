locals {
  lab_state_key = "eks-ai-incident-lab/lab/terraform.tfstate"
}

resource "aws_iam_role" "gha_terraform_plan" {
  name        = "eks-ai-incident-lab-gha-plan"
  description = "GitHub Actions role for planning lab infrastructure."

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
    Purpose = "GitHubTerraformPlan"
  }
}

resource "aws_iam_role_policy" "gha_terraform_plan" {
  name = "lab-network-plan"
  role = aws_iam_role.gha_terraform_plan.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid      = "ListStateBucket"
        Effect   = "Allow"
        Action   = ["s3:ListBucket"]
        Resource = aws_s3_bucket.state.arn
      },
      {
        Sid    = "AccessLabState"
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:PutObject"
        ]
        Resource = "${aws_s3_bucket.state.arn}/${local.lab_state_key}"
      },
      {
        Sid    = "LockLabState"
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:DeleteObject"
        ]
        Resource = "${aws_s3_bucket.state.arn}/${local.lab_state_key}.tflock"
      },
      {
        Sid    = "ReadNetwork"
        Effect = "Allow"
        Action = [
          "ec2:DescribeAvailabilityZones",
          "ec2:DescribeVpcs",
          "ec2:DescribeVpcAttribute",
          "ec2:DescribeSubnets",
          "ec2:DescribeInternetGateways",
          "ec2:DescribeRouteTables",
          "ec2:DescribeTags"
        ]
        Resource = "*"
        Condition = {
          StringEquals = {
            "aws:RequestedRegion" = var.aws_region
          }
        }
      }
    ]
  })
}

output "github_terraform_plan_role_arn" {
  value = aws_iam_role.gha_terraform_plan.arn
}