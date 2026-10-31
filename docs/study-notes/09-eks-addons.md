# 09 — EKS add-ons: networking and ownership

## Verified checkpoint (31 October 2026 IST)

Tan typed `infra/modules/eks/addons.tf` with three `aws_eks_addon` resources: `vpc-cni`, `kube-proxy`, and `coredns`. `terraform fmt -check`, `terraform validate`, and `git diff --check` passed. A read-only plan showed 13 creates, no changes, and no destroys for the whole EKS module. AWS `list-clusters` returned an empty list in `ap-south-1`: **the cluster and add-ons are planned, not deployed**. The plan used a documentation-only `/32` IP; a real operator IP is needed before any deployment.

## The mental model

An EKS **control plane** runs the Kubernetes API and schedules work. An EC2 **node** runs application pods. An **add-on** provides a shared cluster capability that applications need, rather than application-specific business logic. AWS manages installation and update of an *EKS-managed add-on* through the EKS API, while its Kubernetes components still run on provisioned nodes. [AWS EKS add-ons](https://docs.aws.amazon.com/eks/latest/userguide/eks-add-ons.html).

| Add-on | Kubernetes component | Job | Typical symptom if unhealthy |
|---|---|---|---|
| VPC CNI | `aws-node` DaemonSet | Connects pods to VPC networking and assigns pod IPs | Node/pod networking problems; pods may fail to receive IPs |
| kube-proxy | DaemonSet | Maintains node rules that implement Kubernetes Service traffic | Service IPs may not route to healthy pods |
| CoreDNS | Deployment | Resolves names such as `orders.default.svc.cluster.local` | Pods cannot resolve service names |

[AWS networking add-ons](https://docs.aws.amazon.com/eks/latest/userguide/eks-networking-add-ons.html) describe the three roles. A **DaemonSet** runs a copy on each eligible node; a **Deployment** manages a desired number of replicas. With our one-node MVP, multiple CoreDNS replicas would still share one node, so the lab is not highly available.

## Why the Terraform dependencies matter

```text
EKS cluster
  -> VPC CNI and kube-proxy
  -> managed node group
  -> CoreDNS
```

`bootstrap_self_managed_addons = false` avoids installing self-managed copies first. Terraform explicitly requests the EKS-managed versions through `aws_eks_addon`. Each add-on refers to `aws_eks_cluster.this.name`, so Terraform knows the cluster comes first. The node group explicitly waits for VPC CNI and kube-proxy; CoreDNS explicitly waits for the node group so its pods have somewhere to run. `depends_on` changes creation order, not the runtime behavior of Kubernetes. [AWS add-on creation prerequisites](https://docs.aws.amazon.com/eks/latest/userguide/creating-an-add-on.html).

**Managed versus self-managed:** Both are Kubernetes software. With EKS-managed add-ons, EKS exposes their lifecycle through its API and checks compatibility; with self-managed add-ons, operators install/update their Kubernetes objects themselves. In this lab, Terraform owns the EKS add-on resources and EKS manages their cluster objects. Later Argo CD will own application manifests, not these three add-ons. Avoid two controllers trying to own the same fields.

**IAM:** The MVP attaches `AmazonEKS_CNI_Policy` to the node role to keep setup compact. In production, a dedicated pod identity for the VPC CNI narrows permissions. Also test add-on versions against the Kubernetes version during upgrades rather than assuming every version works. [AWS add-on version compatibility](https://docs.aws.amazon.com/eks/latest/userguide/creating-an-add-on.html).

## Troubleshooting and interview practice

Once the cluster exists, compare the AWS add-on status with its Kubernetes workload: `aws eks list-addons --cluster-name <name>` and `kubectl -n kube-system get daemonsets,deployments,pods`. If an add-on is degraded, inspect `aws eks describe-addon --cluster-name <name> --addon-name <name>` and the relevant pod events/logs. These are future runtime checks; today's static plan cannot prove pod health.

**PR #9 security-scan example:** Terraform formatting and validation passed, but Trivy reported `AWS-0040` because the Kubernetes API endpoint is public. This lab also enables the private endpoint and restricts public API access to the operator's `/32`; the nodes use the private endpoint. We documented that specific, reviewable lab exception with an inline Trivy ignore on the cluster resource. The PR check then passed. A `/32` restriction narrows who can reach the public endpoint, but it does not make that endpoint private. For a private-only production endpoint, operators and CI need a connected route into the VPC. [AWS endpoint access](https://docs.aws.amazon.com/eks/latest/userguide/cluster-endpoint.html), [Trivy inline ignore syntax](https://www.trivy.dev/docs/latest/scanner/misconfiguration/config/config/).

**Q: Is an add-on the same as an EKS node group?** No. A node group supplies EC2 capacity. An add-on supplies shared software that runs on that capacity.

**Q: Why install the CNI before nodes?** Nodes and pods need pod networking to become useful. Making this dependency explicit gives Terraform a predictable creation graph.

**Q: Do we need EBS CSI or the AWS Load Balancer Controller now?** No. EBS CSI is for EBS-backed Kubernetes volumes; our planned RDS database is an external managed service. The load balancer controller becomes relevant when we add Kubernetes Ingress. Add only the capability the workload uses. [AWS available add-ons](https://docs.aws.amazon.com/eks/latest/userguide/workloads-add-ons-available-eks.html), [AWS networking add-ons](https://docs.aws.amazon.com/eks/latest/userguide/eks-networking-add-ons.html).
