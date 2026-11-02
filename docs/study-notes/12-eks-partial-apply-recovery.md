# 12 — Partial EKS apply recovery

## Verified incident (3 November 2026 IST)

The [first manual EKS apply](https://github.com/Tech-Sayantan/eks-ai-incident-lab/actions/runs/41513955265) passed OIDC identity, backend initialization, and a saved-plan guard for **13 EKS creates, 0 changes, 0 destroys**. Terraform created the cluster and IAM roles, the operator access entry/policy association, VPC CNI, and kube-proxy. `CreateNodegroup` then failed: EKS could not check whether `AWSServiceRoleForAmazonEKSNodegroup` existed because the GitHub apply role lacked `iam:GetRole`. The workflow failed; Terraform did not roll back the successful resources.

The [read-only recovery plan](https://github.com/Tech-Sayantan/eks-ai-incident-lab/actions/runs/41515532536) succeeded against the saved lab state: **2 to add, 0 to change, 0 to destroy**. The two remaining addresses are `module.eks.aws_eks_node_group.this` and `module.eks.aws_eks_addon.coredns`. The partially created EKS control plane is live and billable even without a node. [AWS EKS pricing](https://aws.amazon.com/eks/pricing/).

## Verified recovery (3 November 2026 IST)

[PR #12](https://github.com/Tech-Sayantan/eks-ai-incident-lab/pull/12) passed Terraform format, validation, and Trivy checks and was squash-merged as `112d07e`. The bootstrap saved plan contained only an in-place update to `aws_iam_role_policy.gha_eks_apply`: **0 added, 1 changed, 0 destroyed**. A JSON guard confirmed the exact new `iam:GetRole` statement and service-linked-role ARN. Applying that saved plan succeeded, and `aws iam get-role-policy` confirmed the statement in AWS. The local saved plan was removed afterward.

The [fresh lab plan](https://github.com/Tech-Sayantan/eks-ai-incident-lab/actions/runs/41516794825) again showed only the node group and CoreDNS: **2 added, 0 changed, 0 destroyed**. The [guarded retry](https://github.com/Tech-Sayantan/eks-ai-incident-lab/actions/runs/41516994586) accepted those exact two creates and completed: **2 added, 0 changed, 0 destroyed**.

AWS read-back showed EKS 1.36 `ACTIVE`, the one-node `t3a.medium` managed node group `ACTIVE` with no reported health issues, and all three add-ons (`vpc-cni`, `kube-proxy`, `coredns`) `ACTIVE` with no reported health issues. `kubectl get nodes` showed one `Ready` node; `kubectl -n kube-system get pods` showed VPC CNI, kube-proxy, and both CoreDNS pods running without restarts. Terraform lab state contained all 13 EKS module resources. These runtime checks establish the cluster is usable for the next application checkpoint; they do not prove application deployment or high availability.

## Why it failed

The **node role** is assumed by EC2 worker nodes after they exist. The **EKS node-group service-linked role** is assumed by the EKS service to manage supporting resources. They are different IAM roles. Our GitHub apply role already had `iam:CreateServiceLinkedRole` for the latter, but EKS first called `iam:GetRole` to check whether it existed. The original `iam:GetRole` permission covered only the lab cluster and node roles. The repair adds `iam:GetRole` for the exact node-group service-linked-role ARN, not all IAM roles. [AWS node-group service-linked role](https://docs.aws.amazon.com/eks/latest/userguide/using-service-linked-roles-eks-nodegroups.html).

## Safe recovery sequence

1. Merge the narrowly scoped bootstrap policy and workflow-guard change after PR checks.
2. Plan the **bootstrap** root. Accept only an in-place update of `aws_iam_role_policy.gha_eks_apply`; apply that reviewed plan. This changes GitHub's AWS permissions, not EKS resources.
3. Re-run the **lab** plan. Require exactly the two remaining creates and no changes or destroys.
4. Run the manual lab apply. It makes a fresh saved plan; the guard accepts either a fresh 13-create lab or this exact two-resource recovery. Verify the cluster, node, and three add-ons after success.

Do not rerun the first 13-create workflow unchanged: its guard would reject a legitimate two-resource plan. Do not manually delete the EKS cluster while Terraform state still owns it. A failed apply requires inspecting both state and AWS before deciding whether to retry or tear down.

## Interview questions

**Why can a failed `terraform apply` still incur cost?** Terraform does not provide an all-or-nothing transaction across AWS APIs. Successful resources remain and are recorded in state; the EKS control plane bills while it exists.

**Why was this not caught by `terraform validate` or the earlier plan?** They checked configuration and proposed changes, but `CreateNodegroup` exercised an AWS service-linked-role permission only at apply time.

**Why not add `iam:GetRole` on `*`?** The denied action and role are known. Limiting the new permission to that ARN keeps the GitHub role's access reviewable.
