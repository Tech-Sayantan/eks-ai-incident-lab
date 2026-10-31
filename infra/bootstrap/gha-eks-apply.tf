resource "aws_iam_role_policy" "gha_eks_apply" {
  name = "lab-eks-apply"
  role = aws_iam_role.gha_terraform_apply.id

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
          "eks:DescribeUpdate",
          "eks:ListAccessEntries",
          "eks:ListAddons",
          "eks:ListAssociatedAccessPolicies",
          "eks:ListClusters",
          "eks:ListNodegroups",
          "eks:ListTagsForResource",
          "eks:ListUpdates"
        ]
        Resource = "*"
        Condition = {
          StringEquals = {
            "aws:RequestedRegion" = var.aws_region
          }
        }
      },
      {
        Sid      = "CreateLabCluster"
        Effect   = "Allow"
        Action   = ["eks:CreateCluster"]
        Resource = "*"
        Condition = {
          StringEquals = {
            "aws:RequestedRegion" = var.aws_region
          }
        }
      },
      {
        Sid    = "ManageLabEks"
        Effect = "Allow"
        Action = [
          "eks:AssociateAccessPolicy",
          "eks:CreateAccessEntry",
          "eks:CreateAddon",
          "eks:CreateNodegroup",
          "eks:DeleteAccessEntry",
          "eks:DeleteAddon",
          "eks:DeleteCluster",
          "eks:DeleteNodegroup",
          "eks:DisassociateAccessPolicy",
          "eks:TagResource",
          "eks:UntagResource",
          "eks:UpdateAddon",
          "eks:UpdateClusterConfig",
          "eks:UpdateNodegroupConfig"
        ]
        Resource = [
          "arn:aws:eks:${var.aws_region}:${var.expected_account_id}:cluster/eks-ai-incident-lab",
          "arn:aws:eks:${var.aws_region}:${var.expected_account_id}:nodegroup/eks-ai-incident-lab/*",
          "arn:aws:eks:${var.aws_region}:${var.expected_account_id}:addon/eks-ai-incident-lab/*",
          "arn:aws:eks:${var.aws_region}:${var.expected_account_id}:access-entry/eks-ai-incident-lab/*"
        ]
        Condition = {
          StringEquals = {
            "aws:RequestedRegion" = var.aws_region
          }
        }
      },
      {
        Sid    = "ManageLabRoles"
        Effect = "Allow"
        Action = [
          "iam:AttachRolePolicy",
          "iam:CreateRole",
          "iam:DeleteRole",
          "iam:DetachRolePolicy",
          "iam:GetRole",
          "iam:GetRolePolicy",
          "iam:ListAttachedRolePolicies",
          "iam:ListInstanceProfilesForRole",
          "iam:ListRolePolicies",
          "iam:TagRole",
          "iam:UntagRole",
          "iam:UpdateAssumeRolePolicy"
        ]
        Resource = [
          "arn:aws:iam::${var.expected_account_id}:role/eks-ai-incident-lab-cluster",
          "arn:aws:iam::${var.expected_account_id}:role/eks-ai-incident-lab-node"
        ]
      },
      {
        Sid    = "PassLabRolesToEks"
        Effect = "Allow"
        Action = ["iam:PassRole"]
        Resource = [
          "arn:aws:iam::${var.expected_account_id}:role/eks-ai-incident-lab-cluster",
          "arn:aws:iam::${var.expected_account_id}:role/eks-ai-incident-lab-node"
        ]
        Condition = {
          StringEquals = {
            "iam:PassedToService" = "eks.amazonaws.com"
          }
        }
      },
      {
        Sid    = "CreateEksServiceLinkedRoles"
        Effect = "Allow"
        Action = ["iam:CreateServiceLinkedRole"]
        Resource = [
          "arn:aws:iam::${var.expected_account_id}:role/aws-service-role/eks.amazonaws.com/AWSServiceRoleForAmazonEKS",
          "arn:aws:iam::${var.expected_account_id}:role/aws-service-role/eks-nodegroup.amazonaws.com/AWSServiceRoleForAmazonEKSNodegroup"
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