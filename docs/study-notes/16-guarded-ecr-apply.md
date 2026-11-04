# 16 — Guarded ECR apply

## What actually happened

Tan typed the manual ECR apply workflow and committed it on `codex/ecr-apply`. The first `git push` failed while the receiver indexed an incomplete pack; the identical retry succeeded. [PR #19](https://github.com/Tech-Sayantan/eks-ai-incident-lab/pull/19) passed `check`, `java`, `node`, and `images`, then merged into `main`.

[The manual apply run](https://github.com/Tech-Sayantan/eks-ai-incident-lab/actions/runs/41887631235) assumed the GitHub Terraform **apply** role through OIDC. Its fresh lab plan showed **2 to add, 0 to change, 0 to destroy**. The `jq` guard returned `true` only after matching the two exact ECR addresses and `create` actions. Terraform applied that saved plan and reported **2 added, 0 changed, 0 destroyed**. The workflow's ECR read-back and a separate CLI read-back under the named `eks-ai-incident-lab` profile both found the repositories in account `923988301700`, region `ap-south-1`.

| Repository | Verified setting |
| --- | --- |
| `eks-ai-incident-lab/orders-api` | `IMMUTABLE`, scan on push, AES256 |
| `eks-ai-incident-lab/payment-simulator` | `IMMUTABLE`, scan on push, AES256 |

The repositories exist but contain no application images yet. The **lab Terraform state** owns them; the separate **bootstrap state** owns the IAM roles and ECR policies that made this apply possible.

## The flow in plain English

`PR checks → merge → manual workflow → temporary OIDC credentials → fresh Terraform plan → exact-change guard → saved-plan apply → AWS read-back`

- **PR checks** proved the code passed tests and static checks. They did not deploy anything.
- **Merge** placed the workflow on `main`; the workflow is restricted to that branch. All four checks passed, but this one-owner lab had no separate human review approval.
- **OIDC** let GitHub request short-lived AWS credentials for the apply role. No AWS access key was stored in GitHub.
- **Plan** asked Terraform what the current AWS state and configuration require.
- **Guard** rejected any result other than the two expected repository creations. This catches unexpected drift or a changed PR before the apply step.
- **Saved-plan apply** used the reviewed plan file, not a newly calculated plan. Terraform recorded the created resources in the lab state.
- **Read-back** queried AWS directly, providing evidence beyond a green Actions badge.

## Production use and troubleshooting

In a team, a reviewer inspects both the code and its checks. A separate deployment gate or approved promotion can control when a workflow applies changes. A plan is time-sensitive: if cloud resources change before apply, generate and review a fresh plan. Exact address/action guards are useful for a small lab or high-risk change; a larger platform would usually use a reviewed plan artifact, policy checks, environment protection, and scoped IAM.

| Symptom | Check and response |
| --- | --- |
| `AccessDenied` during plan | Confirm the assumed role, account, and bootstrap policy; the plan role needs ECR read permissions. |
| `AccessDenied` during apply | Inspect the **apply** role's allowed ECR action and exact repository ARN. |
| Guard prints `false` | Read the plan. Another add, update, or delete appeared; do not bypass the guard. |
| `RepositoryAlreadyExistsException` | Check whether somebody created it outside Terraform; import or reconcile ownership deliberately. |
| CI push gets `ImageTagAlreadyExistsException` | Immutable tags reject overwrites; publish a unique tag and deploy by digest. |
| Later Pod gets `ImagePullBackOff` | Check exact repository/digest, node ECR pull permissions, and connectivity from the node. |

## Interview practice

**Why separate bootstrap and lab state?** Bootstrap holds the credentials and backend resources needed to run the lab. Keeping its state separate avoids the lab deleting its own access path and limits blast radius.

**Why run `terraform apply ecr.tfplan`?** It applies the previously calculated and checked actions. A plain `terraform apply` would recalculate and could include a different set of changes.

**Does a green CI check mean the image is in ECR?** No. The existing `images` job only builds images on a GitHub runner. Publication needs a separate ECR publisher role and push step; deployment needs another Git/Argo promotion.

**Next checkpoint:** Give application CI a dedicated GitHub OIDC publisher role, scan the built images, push unique tags to these repositories, and record the resulting digests.
