# 15 — ECR repositories and Terraform IAM permissions

## What this checkpoint proves

Tan typed `infra/live/lab/ecr.tf` with two private ECR repositories and `infra/bootstrap/gha-ecr.tf` with separate permissions for the GitHub Terraform plan and apply roles. Both Terraform roots returned `Success! The configuration is valid.` and both new files passed `terraform fmt -check`. [PR #17](https://github.com/Tech-Sayantan/eks-ai-incident-lab/pull/17) passed all four required checks and merged. CI validated the code; it did not apply AWS resources.

**Observed bootstrap apply:** A fresh saved plan, run as the named non-root `eks-lab-admin` identity in account `923988301700`, showed exactly two IAM policy creates, no changes, and no destroys. A JSON guard verified the exact resource addresses, create actions, and two ECR repository ARNs. Applying that saved plan returned **2 added, 0 changed, 0 destroyed**. IAM read-back showed the plan role's two read actions and the apply role's eight repository actions; bootstrap state lists both new policy resources. Saved plans were removed afterward. This installed permissions only: neither ECR repository exists yet.

The ECR registry in `ap-south-1` reported `BASIC` scanning. Read-only `DescribeRepositories` calls returned `RepositoryNotFoundException` for both planned repository names before any ECR apply.

## Ownership and why two states matter

- The **bootstrap state** owns the GitHub OIDC roles and their IAM policies. The plan role receives only `ecr:DescribeRepositories` and `ecr:ListTagsForResource`. The apply role receives scoped repository create/read/update/delete actions.
- The **lab state** will own the two repositories. Its provider is pinned to the intended AWS account and `ap-south-1`; the repositories inherit lab tags.
- Both policies use exact repository ARNs, not `*`. The trust policy remains unchanged: GitHub's main-branch subject is allowed to assume the roles, and the new IAM policies decide which ECR actions those assumed roles may perform.
- A separate GitHub publisher role will later push image layers. Giving the Terraform plan role image-push permissions would mix responsibilities.

The repository names are `eks-ai-incident-lab/orders-api` and `eks-ai-incident-lab/payment-simulator`. `for_each` gives each a stable Terraform address. Tags are immutable so a repeated push to the same tag fails; CI will publish a unique build identifier and deployments will use an immutable digest. `force_delete = true` supports final lab teardown even if images remain, so treat `terraform destroy` as destructive for image history.

`scan_on_push = true` enables repository scanning. Before the first apply, verify the registry's scan type: basic scanning has no additional scanning fee, while enhanced Amazon Inspector scanning may incur charges. The PR's Trivy configuration scan checks Terraform configuration; it does not scan the future container image.

## Delivery sequence

1. **Done:** Merge the reviewed Terraform code after required PR checks pass.
2. **Done:** Plan the **bootstrap** root and accept only two new IAM policy resources; apply that exact plan and read back both installed policies.
3. **Done:** Add a separate manual lab workflow guarded for exactly two ECR repository creates; run a fresh plan and apply the saved plan. See [note 16](16-guarded-ecr-apply.md).
4. **Done:** Verify both repositories through the ECR API. Next, add the image publisher role and CI push.

## Real-world failures and interview answers

| Symptom | First check |
| --- | --- |
| Terraform plan gets `AccessDenied` | Which OIDC role did GitHub assume? Was the bootstrap IAM policy actually applied? Is the denied action/resource in its policy? |
| Plan succeeds but apply gets `AccessDenied` | The plan and apply roles are different. Check the apply role's specific ECR action and ARN. |
| `RepositoryAlreadyExistsException` | Check whether a repository was created outside Terraform; import or remove it deliberately instead of blindly retrying. |
| Image push gets `ImageTagAlreadyExistsException` | Immutable tag was reused. Publish a new unique tag or reuse the existing digest. |
| EKS gets `ImagePullBackOff` later | Confirm the image digest exists, node pull permission, network path to ECR, and exact image reference. |

**Q: Repository versus image versus tag versus digest?** A repository stores image versions; an image is the built artifact; a tag is a movable name unless immutability is enforced; a digest identifies exact image content.

**Q: Why did validation pass before AWS permissions existed?** `terraform validate` checks configuration structure locally. A cloud plan/refresh and apply make AWS API calls under the assumed role.

Sources: [ECR tag immutability](https://docs.aws.amazon.com/AmazonECR/latest/userguide/image-tag-mutability.html), [ECR IAM action/resource reference](https://docs.aws.amazon.com/service-authorization/latest/reference/list_ecr.html), [ECR basic scanning](https://docs.aws.amazon.com/AmazonECR/latest/userguide/image-scanning-basic.html).
