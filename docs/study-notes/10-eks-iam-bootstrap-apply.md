# 10 — Apply EKS pipeline IAM through bootstrap

## Verified checkpoint (31 October 2026 IST)

[PR #9](https://github.com/Tech-Sayantan/eks-ai-incident-lab/pull/9) passed its required `check` and was squash-merged to `main` as `154890d`. The named AWS profile resolved to `arn:aws:iam::923988301700:user/eks-lab-admin` in the expected account. A fresh `infra/bootstrap` plan showed **2 to add, 0 to change, 0 to destroy**. Its saved-plan JSON guard accepted only `aws_iam_role_policy.gha_eks_plan_read` and `aws_iam_role_policy.gha_eks_apply`, both creates. Applying that exact saved plan succeeded: **2 added, 0 changed, 0 destroyed**.

AWS `get-role-policy` returned `lab-eks-plan-read` on the GitHub plan role and `lab-eks-apply` on the GitHub apply role. `terraform state list` contained both new policy addresses. S3 read-back showed the bootstrap state key updated, while the lab state key retained its earlier network-apply timestamp. **No EKS cluster was created in this checkpoint.** The local saved plan was deleted after the apply; it was ignored by Git.

## Why this order matters

```text
Git PR/CI -> merge code to main -> bootstrap plan/guard/apply
       -> AWS IAM policies exist -> GitHub OIDC roles can plan/apply EKS later
```

GitHub's OIDC trust policy answers **who can assume the role**. The IAM permission policies answer **what the assumed role can do**. A green PR only checks the proposed configuration; it does not put the policies into AWS. The bootstrap root owns the GitHub roles and their policies in `bootstrap/terraform.tfstate`. The network and future cluster belong to `lab/terraform.tfstate`. [AWS EKS IAM policy examples](https://docs.aws.amazon.com/eks/latest/userguide/security-iam-id-based-policy-examples.html), [Terraform state purpose](https://developer.hashicorp.com/terraform/language/state/purpose).

The plan role can read the specified EKS/IAM information and access the precise lab state/lock objects. The apply role has the additional EKS and IAM actions needed for this lab. `iam:PassRole` permits the apply role to supply the cluster or node role to EKS; it does not let GitHub assume those roles. `iam:CreateServiceLinkedRole` allows EKS to establish its own service-linked roles if needed on first use. [AWS EKS IAM actions](https://docs.aws.amazon.com/service-authorization/latest/reference/list_eks.html), [EKS node-group service-linked role](https://docs.aws.amazon.com/eks/latest/userguide/using-service-linked-roles-eks-nodegroups.html).

## Failure diagnosis and interview practice

| Symptom | First check | Response |
|---|---|---|
| PR green but GitHub plan gets `AccessDenied` | Was the bootstrap IAM apply completed? Which action/resource was denied? | Verify AWS policy read-back; add only the missing permission if justified. |
| Bootstrap plan includes network or EKS resources | `-chdir` root and backend key | Stop: the wrong root/state is being used. |
| State lock cannot be acquired | Is another Terraform run active? | Wait; do not force-unlock without checking the owner. |
| Apply partly fails | AWS API result and `terraform state list` | Terraform does not automatically roll back. Inspect real resources and state before retrying. |

**Q: Why use a saved plan?** The guard inspects the exact operations passed to `terraform apply`. Saved plan files can contain sensitive values, so keep them out of Git and public artifacts. [Terraform plan files](https://developer.hashicorp.com/terraform/cli/commands/plan), [apply behavior](https://developer.hashicorp.com/terraform/cli/commands/apply).

**Q: Did deploying IAM deploy EKS?** No. The bootstrap root installed permissions. A separate manual run from the lab root will later plan and create EKS resources.

**Q: Is a green PR proof the AWS role works?** No. Static checks validate code. An AWS-backed plan or apply tests the live identity, policy, state, region, and account.
