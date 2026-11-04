# 17 — Image publisher role and OIDC

## Verified checkpoint

Tan typed `infra/bootstrap/gha-image-publisher.tf`. [PR #21](https://github.com/Tech-Sayantan/eks-ai-incident-lab/pull/21) changed only that file, passed the four required checks, and merged. Validation also returned `Success! The configuration is valid.` The role did **not** exist in AWS before apply.

From a fresh local checkout, a saved **bootstrap** plan showed exactly `aws_iam_role.gha_image_publisher` and `aws_iam_role_policy.gha_image_publisher` as creates: **2 to add, 0 to change, 0 to destroy**. A JSON guard matched those exact addresses and `create` actions. Applying the same plan returned **2 added, 0 changed, 0 destroyed**. IAM read-back and Terraform state both confirmed the role and policy. The saved plan was removed, and the S3 state lock was absent afterward.

The role ARN is `arn:aws:iam::923988301700:role/eks-ai-incident-lab-gha-image-publish`. Its trust condition requires the GitHub OIDC audience `sts.amazonaws.com` and this repository's `main` branch subject. Its policy grants `ecr:GetAuthorizationToken` on `*`, then limits image upload and `DescribeImages` actions to the two lab repository ARNs in `ap-south-1`. The role has no Terraform, Kubernetes, or general AWS administration permissions.

The two ECR repositories still contain **zero images**. Creating a publisher role grants an ability; it does not run a build or push.

## Concept in plain English

An **IAM role** is an identity a trusted caller can temporarily assume. Its **trust policy** answers *who may assume it?* Here, GitHub Actions on `main` may request short-lived credentials through OIDC. Its **permissions policy** answers *what may the assumed identity do?* Here, it may authenticate to ECR and publish only to the two named repositories. GitHub does not store a long-lived AWS access key for this flow.

ECR registry authentication is an account-level operation, so `GetAuthorizationToken` needs resource `*`. The actual image upload actions are scoped to exact repository ARNs. AWS's [ECR push policy](https://docs.aws.amazon.com/AmazonECR/latest/userguide/image-push-iam.html) shows this split.

## Real-world failure: synced Git and Terraform files

The original checkout under `~/Documents/Codex` repeatedly returned macOS `mmap failed: Operation canceled` during Git operations. A failed fast-forward left a zero-byte local copy of the new role file; the committed GitHub copy remained intact. The original `Documents` directory carried File Provider metadata, and the 790 MB Terraform AWS provider binary was marked `dataless`. Terraform could not finish reading that cloud-managed binary. An interrupted **plan** left its S3 lock. After confirming the original plan process was gone and the lock belonged to it, the exact lock ID was force-unlocked.

A fresh clone at `~/Developer/eks-ai-incident-lab` downloaded the pinned provider, initialized the S3 backend, and completed the plan and apply. The original checkout was repaired and retained; ongoing work moved to the new clone. Git's [FAQ](https://git-scm.com/docs/gitfaq) warns that cloud-syncing a Git repository can cause object and ref problems. Keep active source and Terraform provider files on local storage; use GitHub and remote Terraform state for sharing.

## Troubleshooting and interview practice

| Symptom | First check |
| --- | --- |
| `AssumeRoleWithWebIdentity` denied | Compare the token audience and subject with the role trust policy; verify the workflow runs on `main`. |
| ECR login denied | Check `ecr:GetAuthorizationToken` on `*` and the assumed role ARN. |
| Docker push denied | Check the exact repository ARN and missing upload action in the publisher policy. |
| Terraform says state is locked | Identify the operation and owner; verify no process still uses that lock before force-unlocking its exact ID. |
| Git or Terraform stalls in `Documents` | Check File Provider or cloud-sync status; use a local checkout and reinitialize the pinned provider. |

**Q: Why a separate publisher role?** CI only needs to upload images. Giving it the Terraform apply role would let a compromised build job alter infrastructure.

**Q: Does the trust policy grant ECR access?** No. Trust allows GitHub to assume the role; the attached IAM policy grants ECR actions after assumption.

**Q: Which state owns this role?** The bootstrap state. The lab state owns the ECR repositories. CI will publish images, and Git/Argo CD will later select the deployment digest.

**Next checkpoint:** Add a GitHub Actions job that tests, builds, scans, and pushes both images with unique tags, then records their immutable digests.
