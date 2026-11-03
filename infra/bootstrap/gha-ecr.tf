locals {
  lab_ecr_repository_arns = [
    for name in ["orders-api", "payment-simulator"] :
    "arn:aws:ecr:${var.aws_region}:${var.expected_account_id}:repository/eks-ai-incident-lab/${name}"
  ]
}

resource "aws_iam_role_policy" "gha_ecr_plan_read" {
  name = "lab-ecr-plan-read"
  role = aws_iam_role.gha_terraform_plan.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Sid    = "ReadLabRepositories"
      Effect = "Allow"
      Action = [
        "ecr:DescribeRepositories",
        "ecr:ListTagsForResource"
      ]
      Resource = local.lab_ecr_repository_arns
    }]
  })
}

resource "aws_iam_role_policy" "gha_ecr_apply" {
  name = "lab-ecr-apply"
  role = aws_iam_role.gha_terraform_apply.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Sid    = "ManageLabRepositories"
      Effect = "Allow"
      Action = [
        "ecr:CreateRepository",
        "ecr:DeleteRepository",
        "ecr:DescribeRepositories",
        "ecr:ListTagsForResource",
        "ecr:PutImageScanningConfiguration",
        "ecr:PutImageTagMutability",
        "ecr:TagResource",
        "ecr:UntagResource"
      ]
      Resource = local.lab_ecr_repository_arns
    }]
  })
}
