# 07 — Protected PR gate and network apply role

## Verified checkpoint (29 October 2026 IST)

[PR #4](https://github.com/Tech-Sayantan/eks-ai-incident-lab/pull/4) made the Terraform `check` job run on every pull request. GitHub branch protection for `main` now requires a PR, the current branch, and that passing check; it enforces the rule for admins and blocks force pushes and deletion. It requires zero formal review approvals for this solo lab.

Tan typed `infra/bootstrap/gha-terraform-apply.tf`. [PR #5](https://github.com/Tech-Sayantan/eks-ai-incident-lab/pull/5) passed `check`, received no formal review, and was squash-merged by `Tech-Sayantan` as `b1a9dbb`. A local bootstrap plan showed exactly two IAM additions. Tan then applied the saved plan with the named non-root profile. AWS reads confirmed the new `eks-ai-incident-lab-gha-apply` role and its `lab-network-apply` inline policy exist in account `923988301700`. No lab-tagged VPC or lab state object existed at the subsequent check.

## Four separate decisions

```text
Automated check passes -> human review (if required) -> merge -> deploy gate -> apply
```

A green check reports what automation tested. A PR approval is a recorded human review; it does not itself merge the PR. A merge may be performed by an authorized person, by optional auto-merge once requirements pass, or by a merge queue. This repository has auto-merge disabled, and PR #5 was merged manually. A deployment environment approval is a *separate* gate for a workflow job after code is merged. In a solo lab, manual workflow dispatch is an operator go/no-go, not an independent peer approval.

## What the apply role can do

OIDC trust restricts role assumption to this repository's immutable identity on `main`. Its policy can access only the lab state object and lock file in S3; its EC2 actions cover the current network module and are limited to `ap-south-1`. The EC2 write statement uses `Resource = "*"`, so it is action-and-Region scoped rather than restricted to a specific VPC. There are no EKS, RDS, EC2 instance-launch, or IAM write permissions. In production, use separate accounts, stronger review and deployment controls, and resource/tag conditions where supported.

## Troubleshooting and interview practice

- **PR passed but role absent:** checks validate code; the bootstrap `terraform apply` creates AWS IAM resources.
- **PR approval versus merge:** the reviewer can approve, but an authorized person or configured automation performs the merge. The same person need not do both.
- **Manual deploy versus peer approval:** a `workflow_dispatch` click records an operator action; a required environment reviewer is a distinct GitHub gate. Self-review in a solo repository should not be described as independent approval.
- **Why save a Terraform plan?** A saved plan lets `apply` execute the exact inspected actions. Inspect it first; a saved plan may contain sensitive values and must stay out of Git and public artifacts.

Sources: [GitHub auto-merge](https://docs.github.com/en/pull-requests/how-tos/merge-and-close-pull-requests/automatically-merging-a-pull-request), [GitHub deployments and environments](https://docs.github.com/en/actions/reference/workflows-and-actions/deployments-and-environments), [Terraform saved plans](https://developer.hashicorp.com/terraform/cli/commands/plan), [AWS EC2 IAM conditions](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/iam-policies-for-amazon-ec2.html).
