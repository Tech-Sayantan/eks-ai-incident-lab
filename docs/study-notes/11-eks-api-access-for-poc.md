# 11 — EKS API access for the POC

## POC decision (2 November 2026 IST)

The original EKS plan limited the public Kubernetes API endpoint to Tan's current public IPv4 `/32`. Home, VPN, and mobile-network IPs can change. For this short-lived practice cluster, we removed the operator CIDR variable, the `EKS_OPERATOR_CIDR` GitHub secret requirement, and the checks in both manual workflows. The EKS module now explicitly sets `public_access_cidrs = ["0.0.0.0/0"]` and keeps `endpoint_private_access = true`. This is a code decision, **not evidence of a deployed cluster**. A new AWS-backed plan and explicit apply decision are still required.

## What this exposes, and what it does not

`0.0.0.0/0` lets any IPv4 source *reach* the public Kubernetes API endpoint. It does not grant permission to operate the cluster. EKS authenticates users through AWS IAM, and Kubernetes access policies/RBAC authorize actions. Our Terraform config creates a cluster access entry and associates `AmazonEKSClusterAdminPolicy` with the named lab operator. The GitHub Terraform plan/apply roles call AWS APIs through OIDC; they do not need Tan's home IP to plan or create the cluster. Nodes communicate with the Kubernetes API through the enabled private endpoint. [AWS endpoint access](https://docs.aws.amazon.com/eks/latest/userguide/cluster-endpoint.html), [AWS identity and access guidance](https://docs.aws.amazon.com/eks/latest/best-practices/identity-and-access-management.html).

This public endpoint is a deliberate **temporary lab exception**. For production, allow only trusted public CIDRs with private access enabled, or use a private-only endpoint and a route into the VPC (for example, VPN or a controlled runner). A private-only endpoint would block `kubectl` from Tan's laptop without that route. Tear down the paid EKS cluster after practice; leaving an open public API reachable indefinitely increases exposure even though authentication remains required.

## Interview and troubleshooting

**Q: Does `0.0.0.0/0` make the cluster anonymous?** No. It changes network reachability, not IAM authentication or Kubernetes authorization. Explain both gates separately.

**Q: Why enable private access if public access is open?** In-VPC nodes can use the private endpoint. Public access is for the operator's laptop in this lab.

**Q: Why did the old `/32` approach break?** A dynamic public IP may change. Updating a GitHub secret alone would not change an existing cluster; Terraform would need another apply. The POC removes that maintenance step.

**Issue: `kubectl` gets `Unauthorized` despite reaching the API.** Check `aws sts get-caller-identity --profile eks-ai-incident-lab`, the EKS access entry/policy association, and kubeconfig identity. Network reachability and authorization are separate checks.

**Issue: `kubectl` times out.** Check endpoint status and DNS, network/VPN/firewall path, and whether the cluster endpoint is public or private. An IAM problem usually returns an authentication/authorization error rather than a network timeout.
