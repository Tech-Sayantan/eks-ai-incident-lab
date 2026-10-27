# 03 — VPC networking foundations

## Lab evidence and boundary

Tan typed the first `network` module and `infra/live/lab` caller. On 27 October 2026, Trunks inspected those files and independently verified `terraform fmt -check`, `terraform validate`, and a read-only plan using the named non-root AWS profile in `ap-south-1`: **8 to add, 0 to change, 0 to destroy**. This is a proposal, not evidence of deployed resources. The lab root currently has no remote backend or applied state.

The proposed eight resources are one VPC, one Internet Gateway, two public subnets in different Availability Zones, one public route table, one default route to the gateway, and two route-table associations. The future public subnets have automatic public IPv4 assignment and the `kubernetes.io/role/elb=1` tag for internet-facing load balancer discovery. No NAT gateway, load balancer, EKS cluster, node, or RDS instance is in this plan.

## Explain the network in an interview

- A VPC belongs to one AWS Region and spans that Region's Availability Zones. A subnet belongs to exactly one AZ; two subnets in different AZs provide distinct failure domains.
- `10.42.0.0/16` is the VPC address space. The public subnets use `10.42.0.0/24` and `10.42.1.0/24`. AWS reserves five IPv4 addresses per subnet, leaving 251 assignable addresses in each `/24`.
- A subnet is public when its associated route table has an internet route to an Internet Gateway. A workload additionally needs a public IP and an allowing security-group rule for inbound IPv4 access. The VPC's local route handles traffic within the VPC.
- The EKS cluster needs subnets in at least two AZs, each with enough free IP addresses. Public subnets are supported, but AWS recommends private subnets for nodes where feasible. This short-lived lab chooses public nodes to avoid an always-on NAT gateway, then constrains access with security groups in the EKS checkpoint. Public IPv4 addresses assigned to future resources incur charges.
- A module groups resources behind inputs and outputs. The root module chooses the Region, account guard, AZs and CIDRs. Its output IDs become inputs to later infrastructure.

## Security group versus network ACL

| Question | Security group (SG) | Network ACL (NACL) |
|---|---|---|
| Where? | Resource network interface | Subnet boundary |
| Rules? | Allow only; all applicable rules evaluated | Allow and deny; lowest numbered matching rule wins |
| Return packet? | Automatically allowed for an allowed connection (stateful) | Must be allowed by a matching rule in the reverse direction (stateless) |
| Typical use? | Main access policy for nodes, load balancers, databases | Additional subnet-wide guardrail or explicit CIDR deny |

Every VPC has a default SG and NACL. Subnets not explicitly associated with a custom NACL use the VPC's default NACL, which initially allows inbound and outbound traffic. This lab does not create a custom NACL now. Later EKS security groups should allow only the required control-plane, node and ALB paths. A custom NACL requires careful return/ephemeral-port rules; an overly restrictive one can break traffic even when SG rules are correct.

## Production scenarios and troubleshooting

1. **Node does not join EKS:** confirm subnet AZ and free IPs, public-IP assignment for public nodes, default route, EKS endpoint access, node IAM role, and SG rules. Do not assume the subnet tag or route alone gives internet connectivity.
2. **ALB stays pending:** inspect the controller event/log, the `kubernetes.io/role/elb` subnet tag, two suitable AZs, available subnet IPs, and controller IAM permissions.
3. **Connection times out despite an open SG:** inspect the subnet route, NACL in both directions, the destination listener, and where the packet actually arrives. VPC Flow Logs can help with accepted/rejected traffic.
4. **Network range overlaps an office/VPN network:** select a non-overlapping VPC CIDR before connecting networks; changing an established VPC CIDR/subnet design later can require disruptive migration.
5. **Cost surprise:** a VPC, subnet, route table and Internet Gateway do not by themselves imply a running EKS bill. NAT gateways, nodes, public IPv4 addresses, load balancers, data transfer and EKS control-plane hours are later cost-bearing choices. Estimate in the target Region before apply.

## Delivery and state decision

The lab's AWS infrastructure will use a PR and GitHub Actions pipeline. First extend CI to format, initialize without a backend, validate and scan both Terraform roots. Then add the lab root's own S3 state key, distinct from bootstrap. A later OIDC planning role will allow an internal PR plan; a separate controlled apply path on the trusted main revision will require Tan's deliberate trigger/approval. Do not automatically apply an old PR plan after merge. This repository is private and the connected GitHub account reports the Free plan. GitHub's required-reviewer environment protection is unavailable for this combination, so PR review/merge plus a manual deployment trigger will be the explicit gate. Bootstrap IAM may need a one-time local apply to grant the pipeline its initial scoped permissions.

## Interview quick answers

- **VPC vs subnet scope?** VPC: Region. Subnet: one AZ within that Region.
- **What makes a subnet public?** Its associated route table points internet-bound traffic to an Internet Gateway. Individual resources still need public addressing and permitted traffic rules.
- **SG vs NACL?** SG is resource-level, allow-only and stateful; NACL is subnet-level, allow/deny and stateless.
- **Why two AZs?** EKS requires cluster subnets in at least two AZs; distributing workload capacity reduces single-AZ exposure.
- **Does `terraform plan` create anything?** No. It reads current state and APIs and proposes operations; `apply` performs them.

Sources: [AWS VPC basics](https://docs.aws.amazon.com/vpc/latest/userguide/vpc-subnet-basics.html), [subnets](https://docs.aws.amazon.com/vpc/latest/userguide/configure-subnets.html), [SG/NACL comparison](https://docs.aws.amazon.com/vpc/latest/userguide/infrastructure-security.html), [default NACL](https://docs.aws.amazon.com/vpc/latest/userguide/default-network-acl.html), [EKS networking](https://docs.aws.amazon.com/eks/latest/userguide/network-reqs.html), [Terraform S3 backend](https://developer.hashicorp.com/terraform/language/backend/s3), [GitHub environment availability](https://docs.github.com/en/actions/how-tos/deploy/configure-and-manage-deployments/manage-environments).
