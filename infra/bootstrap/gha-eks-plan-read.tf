resource "aws_iam_role_policy" "gha_eks_plan_read" {
  name = "lab-eks-plan-read"
  role = aws_iam_role.gha_terraform_plan.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "ReadEks"
        Effect = "Allow"
        Action = [
          "eks:DescribeAccessEntry",
          "eks:DescribeAddon",
          "eks:DescribeAddonVersions",
          "eks:DescribeCluster",
          "eks:DescribeNodegroup",
          "eks:ListAddons",
          "eks:ListAssociatedAccessPolicies",
          "eks:ListClusters",
          "eks:ListNodegroups",
          "eks:ListTagsForResource"
        ]
        Resource = "*"
        Condition = {
          StringEquals = {
            "aws:RequestedRegion" = var.aws_region
          }
        }
      },
      {
        Sid    = "ReadLabRoles"
        Effect = "Allow"
        Action = [
          "iam:GetRole",
          "iam:GetRolePolicy",
          "iam:ListAttachedRolePolicies",
          "iam:ListRolePolicies"
        ]
        Resource = [
          "arn:aws:iam::${var.expected_account_id}:role/eks-ai-incident-lab-cluster",
          "arn:aws:iam::${var.expected_account_id}:role/eks-ai-incident-lab-node"
        ]
      },
      {
        Sid      = "ReadSecurityGroups"
        Effect   = "Allow"
        Action   = ["ec2:DescribeSecurityGroups"]
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