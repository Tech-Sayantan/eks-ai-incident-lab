# 01 — Terraform bootstrap and GitHub OIDC

## What we built

The bootstrap root creates one private S3 bucket for Terraform state. We first created that bucket while Terraform used local state. After the bucket existed, `terraform init -migrate-state` copied the bootstrap state to a dedicated key in the bucket. Versioning keeps older state objects; S3 lockfiles coordinate concurrent writers. The backend stores Terraform's state, while the AWS provider makes API calls to manage resources.

The same bootstrap root also creates an IAM OIDC provider for GitHub and a role restricted to this repository's immutable owner/repository IDs and the `main` branch. The role currently has no AWS resource permission policy. A manual GitHub Actions smoke test successfully assumed the role and printed its STS identity.

**Verified:** the remote state lists six S3 resources, one GitHub OIDC provider, and one IAM role. A fresh Terraform plan showed no changes. No EKS cluster, ECR repository, or RDS database exists yet.

## Mental models

### State, provider, and backend

| Terraform term | Think of it as | Why it matters |
|---|---|---|
| Configuration (`.tf`) | Desired infrastructure | Reviewed and versioned in Git |
| State | Terraform's record mapping addresses to real objects | Can contain sensitive attributes; protect it |
| AWS provider | Plugin that calls AWS APIs | Uses the selected AWS identity and region |
| S3 backend | Location where state lives | Must exist before Terraform can initialize it |
| State lock | Coordination for one writer at a time | Prevents concurrent applies from clobbering state |
| S3 versioning | Older copies of the state object | Helps recovery; does not replace locking |

Bootstrap is a dependency problem: the backend bucket cannot host state before it exists. Use local state for the first apply, then migrate it. The bucket can hold the state that describes itself because Terraform created the bucket before switching its state storage.

### State boundaries in this lab

The two **root configurations** use one S3 bucket but different object keys:

| Root | S3 object key | What it owns |
|---|---|---|
| `infra/bootstrap` | `eks-ai-incident-lab/bootstrap/terraform.tfstate` | State bucket, GitHub OIDC provider, and CI IAM roles/policies |
| `infra/live/lab` | `eks-ai-incident-lab/lab/terraform.tfstate` | Lab VPC/network and, after deployment, EKS resources |

Each root has its own backend block and state. The child modules `modules/network` and `modules/eks` contribute resources to the **lab root's** state; they do not make state files of their own. The bootstrap bucket was first created with local state, then `terraform init -migrate-state` copied that state to the bootstrap key. The lab key was written when the network was applied. A PR, `terraform validate`, or a plan does not deploy EKS or add its resources to state. A successful EKS apply will record them in the existing lab key. Both keys use separate temporary `.tflock` objects during locking. [Terraform S3 backend](https://developer.hashicorp.com/terraform/language/backend/s3), [purpose of state](https://developer.hashicorp.com/terraform/language/state/purpose).

**Multiple projects in one AWS account:** Separate states are normal. A shared VPC can have one network state, while each application or cluster has its own state and lifecycle. The states may use different keys in one bucket or separate backends. Give each real resource one Terraform owner; other projects can look up its VPC/subnet IDs through AWS data sources or carefully shared outputs. Splitting state reduces the scope of a mistaken apply but requires explicit dependencies between roots. For this compact lab, network and EKS share one lab state so the cluster can directly reference `module.network.public_subnet_ids`. [Terraform state mapping](https://developer.hashicorp.com/terraform/language/state/purpose), [remote state outputs and access caveat](https://developer.hashicorp.com/terraform/language/state/remote-state-data).

### OIDC and IAM

```text
GitHub workflow → signed OIDC token → AWS checks issuer/audience/subject
                → IAM role trust matches → STS returns temporary credentials
```

- **OIDC issuer:** GitHub's token service. AWS registers it as an IAM OIDC provider.
- **Audience (`aud`):** intended receiver, here `sts.amazonaws.com`.
- **Subject (`sub`):** the GitHub repository and job context. This lab restricts it to one repository and the `main` branch.
- **Role trust policy:** who may assume the role.
- **Role permission policy:** what the assumed role may do after assuming it.
- **STS:** AWS service that issues temporary role credentials.

A successful `sts get-caller-identity` proves federation. It does not prove permission to create EKS, read state, or push an image. Those permissions need separate, scoped policies.

## Real-world choices

- Give CI separate plan and apply identities. A PR plan should not inherit deploy permissions.
- Never put long-lived AWS access keys in GitHub secrets when OIDC can supply temporary credentials.
- Match OIDC trust to the exact repository and allowed branch or environment. GitHub's newer immutable `sub` format includes numeric IDs, which reduces name-reuse risk.
- Treat the bootstrap state bucket separately from ordinary cluster teardown. Preserve state until managed resources and dependencies are accounted for.
- Use a named non-root profile locally. The shell prompt's AWS region reflects its selected profile or environment, not necessarily the region of a command that used a temporary per-command override.

## Troubleshooting

| Symptom | Likely cause | First check |
|---|---|---|
| Backend initialization fails before bucket creation | Backend bucket does not exist | Bootstrap locally, then migrate |
| Provider targets wrong account | Wrong local profile or environment credential | `aws sts get-caller-identity` and account guard |
| `AssumeRoleWithWebIdentity` denied | OIDC `aud` or `sub` mismatch | Exact repo IDs, branch, and role trust policy |
| GitHub assumes role but AWS API is denied | Role lacks the needed permission policy | Separate trust from authorization |
| Prompt says `us-east-1` during this lab | Shell uses another AWS profile | `export AWS_PROFILE=eks-ai-incident-lab`; check effective region |

## Interview practice

1. **Why does Terraform need state?** To map declared resource addresses to real objects and retain attributes used in plans.
2. **Why local state first?** The S3 backend bucket is not yet present; after creation, migrate state to it.
3. **Locking versus versioning?** Locking prevents concurrent writes; versioning retains prior object versions for recovery.
4. **What does OIDC replace?** Long-lived AWS credentials stored in CI. GitHub presents a signed, short-lived identity token instead.
5. **Trust versus permissions?** Trust controls who can assume a role; permissions control what that role can do.
6. **What does the OIDC smoke test prove?** GitHub can assume the role and obtain temporary credentials. It does not prove deployment access.

## References

- [Terraform S3 backend](https://developer.hashicorp.com/terraform/language/backend/s3)
- [GitHub OIDC reference](https://docs.github.com/en/actions/reference/security/oidc)
- [AWS role trust for GitHub](https://docs.aws.amazon.com/IAM/latest/UserGuide/id_roles_create_for-idp_oidc.html)
