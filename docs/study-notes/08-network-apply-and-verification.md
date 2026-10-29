# 08 — Network apply and verification

## Verified checkpoint (29 October 2026 IST)

Tan typed the guarded manual workflow. [PR #7](https://github.com/Tech-Sayantan/eks-ai-incident-lab/pull/7) passed the required `check` and was squash-merged to `main` as `a011f56`. The [manual apply run](https://github.com/Tech-Sayantan/eks-ai-incident-lab/actions/runs/40923313646) succeeded: OIDC role assumption, account check, backend initialization, fresh plan, eight-create guard, saved-plan apply, and output steps all passed. Merge alone did not trigger deployment; the `workflow_dispatch` run did.

AWS read-back in `ap-south-1` confirmed VPC `vpc-050954c44f1309783` (`10.42.0.0/16`), with public subnets `10.42.0.0/24` in `ap-south-1a` and `10.42.1.0/24` in `ap-south-1b`. Both subnets are associated with the lab route table. Its active `0.0.0.0/0` route targets Internet Gateway `igw-06dd92ac9945a7736`. Terraform outputs returned the same VPC and subnet IDs. `terraform state list` showed eight managed network resources plus one read-only availability-zone data source. This is live-network evidence, not an EKS deployment.

## The flow in plain English

```text
PR check -> squash merge to main -> operator starts workflow
  -> GitHub OIDC assumes the AWS apply role -> Terraform reads remote state
  -> fresh plan -> guard accepts exactly eight creates -> apply saved plan
  -> Terraform records AWS IDs in state -> read back from AWS
```

**Why save the plan?** The workflow checks the exact plan it later applies. This checkpoint's guard rejects updates, deletes, and unexpected resource addresses. After this first run, a repeat run would normally have no creations, so the deliberately narrow guard would stop it. Do not treat a failed repeat as proof the VPC vanished; inspect the current plan and AWS first.

**What makes these subnets public?** Their associated route table has a default IPv4 route to an attached Internet Gateway. The subnet setting to assign a public IPv4 address applies to future network interfaces; creating a subnet did not create an instance or allocate a public address. Routing alone does not guarantee an application is reachable: an instance or load balancer, address, security-group rules, and a healthy listener would also be needed. [AWS explains these requirements](https://docs.aws.amazon.com/vpc/latest/userguide/VPC_Internet_Gateway.html).

**What does state prove?** It maps Terraform resource addresses to AWS object IDs. It is useful evidence of what Terraform manages, but an AWS API read confirms the object still exists. The data source in `state list` reads available AZs; it is not a ninth managed network resource. [Terraform saved-plan behavior](https://developer.hashicorp.com/terraform/cli/commands/apply).

## Real-world failures and interview practice

| Symptom | First check | Likely fix |
|---|---|---|
| PR green, VPC absent | Was the manual apply run started and successful? | Run the approved workflow from `main`; a merge is not deployment. |
| OIDC step denied | Role trust, repo/branch claim, account ID | Correct the trust or workflow identity; do not add long-lived AWS keys. |
| Guard returns `false` | Inspect the fresh plan and current state | Investigate drift or partial apply before changing the guard or rerunning. |
| Subnet has no internet access | Route-table association, IGW, public IP, security group | Repair the missing prerequisite; a subnet name alone changes no routing. |

**Interview Q1: What is the difference between CI and CD here?** CI checked the PR. CD was a separate, operator-started workflow that planned and applied the merged Terraform configuration.

**Interview Q2: Why verify both Terraform and AWS?** State shows Terraform ownership; AWS read-back shows the real network and routes. Together they catch a missing deployment or drift more reliably than a green PR check.

**Interview Q3: Why two subnets?** They are in different Availability Zones, so later workloads can be placed across AZs. This network alone does not provide workload high availability.

Sources: [GitHub manual workflows](https://docs.github.com/en/actions/how-tos/manage-workflow-runs/manually-run-a-workflow), [Terraform apply with a saved plan](https://developer.hashicorp.com/terraform/cli/commands/apply), [AWS Internet Gateway routing](https://docs.aws.amazon.com/vpc/latest/userguide/VPC_Internet_Gateway.html).
