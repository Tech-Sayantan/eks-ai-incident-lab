# 05 — GitHub OIDC plan role

## Observed checkpoint

Tan typed `infra/bootstrap/gha-terraform-plan.tf` on branch `codex/gha-plan-role`. On 29 October 2026, Trunks independently checked formatting and validation, verified the named AWS profile points to account `923988301700`, and ran a live bootstrap plan. The result was **2 to add, 0 to change, 0 to destroy**: one IAM role and one inline policy. [PR #2](https://github.com/Tech-Sayantan/eks-ai-incident-lab/pull/2) passed its static CI check and was squash-merged without a review approval. Tan then ran the local bootstrap apply; a subsequent AWS IAM read confirmed `arn:aws:iam::923988301700:role/eks-ai-incident-lab-gha-plan` exists. The role has not yet been exercised from a GitHub Actions cloud-plan workflow.

## The concept in plain English

GitHub issues a signed OIDC token describing the workflow's identity. AWS STS checks that token against the IAM role's **trust policy** and returns temporary credentials. The role's **permission policy** then decides which AWS API calls those credentials allow. `aud = sts.amazonaws.com` checks the intended recipient; `sub` pins the immutable repository identity and `main` branch. The existing identity-smoke role proves federation, while this new role adds access needed for Terraform's lab plan.

The policy can list the state bucket, access only the lab's exact state object and `.tflock` object, and run specific EC2 Describe operations in `ap-south-1`. Terraform's S3 backend needs lock writes and documents state object read/write access. The role has no EC2 Create, Modify or Delete actions; however, its state write permission is still powerful. Future secrets can appear in Terraform state, so only reviewed `main` will run the cloud plan. PR jobs remain format, validate and Trivy checks without AWS credentials.

## Delivery order

```text
local plan -> PR with static checks -> deliberate merge -> local bootstrap apply
           -> GitHub Actions manual cloud-plan workflow -> verify role and plan
```

The role is declared in the bootstrap stack, so a local administrator applies it once. GitHub Actions cannot assume a role that does not exist. Merging the PR only publishes the desired configuration; it does not create the IAM role. The repository is now public, but `main` has no branch protection rule; Tan must inspect results and choose when to merge until a rule is configured.

## Production issues and interview answers

- **`AssumeRoleWithWebIdentity` denied:** check the OIDC provider ARN, `aud`, exact `sub`, branch, role ARN and workflow `id-token: write` setting.
- **S3 AccessDenied during plan:** compare the configured backend bucket/key and `.tflock` path with the policy resources. Do not broaden access to every state object merely to clear one error.
- **Why can this role write state if it is called a plan role?** The S3 backend uses write permissions for state and locking. The role is scoped by workflow identity and state key, and lacks infrastructure mutation actions; it is not a fully read-only identity.
- **Why replan after merge?** A speculative branch plan may be stale. Generate and review a fresh plan from the trusted revision against current remote state before applying.
- **Does a green PR check deploy IAM?** No. It verifies code. The bootstrap apply is a separate AWS operation.

Sources: [AWS IAM OIDC roles](https://docs.aws.amazon.com/IAM/latest/UserGuide/id_roles_create_for-idp_oidc.html), [GitHub OIDC in AWS](https://docs.github.com/en/actions/how-tos/secure-your-work/security-harden-deployments/oidc-in-aws), [Terraform S3 backend permissions](https://developer.hashicorp.com/terraform/language/backend/s3), [Terraform plan and apply](https://developer.hashicorp.com/terraform/cli/commands/plan).
