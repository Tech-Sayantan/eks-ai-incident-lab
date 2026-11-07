# 26 — Import and retire the public endpoint

Tan asked to stop paying for the lab ALB and continue the investigator through internal access. First we recorded the resources created through the console in Terraform. The fresh plan said four imports, zero adds, zero updates and zero destroys. The apply imported the ACM certificate, Route 53 child hosted zone, verification CNAME and A Alias into the separate `eks-ai-incident-lab/edge/terraform.tfstate` key. A second plan reported no changes. HTTPS still returned 200 after adoption.

Terraform owned the Alias and certificate configuration. Argo owned the desired Ingress. AWS Load Balancer Controller owned the ALB and its AWS resources. We retired the endpoint through those owners.

1. [PR #28](https://github.com/Tech-Sayantan/eks-ai-incident-lab/pull/28) set `ingress.enabled` to false. All four checks passed. Comparing rendered charts showed the Ingress disappeared and the other six resources matched.
2. After merge, Argo showed only the Orders Ingress needed pruning. A selective sync pruned that Ingress and reported Synced, Healthy and Succeeded at `42fbc54`.
3. AWS APIs confirmed the ALB, target group and the ALB's network interfaces were gone. The dedicated CloudWatch health alarm and SNS topic were deleted and verified absent.
4. A saved Terraform plan removed exactly the A Alias. We then removed that Alias from configuration and ran a fresh plan. It reported no changes. The [edge configuration](https://github.com/Tech-Sayantan/eks-ai-incident-lab/tree/codex/adopt-edge/infra/live/edge) records the retained resources.
5. Both app Pods were Ready with zero restarts. A temporary local port-forward returned HTTP 200 with `{"status":"UP"}` after ALB removal. This is the path we can use while learning the investigator.

The child hosted zone, validation CNAME and issued ACM certificate remain tracked. The certificate has no load balancer attachment. The Cloudflare parent delegation has four lab NS records. Cloudflare's permanent-delete dialog requires action-time confirmation for those records. Remove that delegation and allow its TTL to expire before deleting the child hosted zone. See [AWS's hosted-zone deletion guidance](https://docs.aws.amazon.com/Route53/latest/DeveloperGuide/DeleteHostedZone.html).

**Why import first?** The state became a record of which existing AWS objects match the configuration. The import-only plan let us check that adoption would keep the actual resource settings.

**Why prune Ingress before removing its controller?** The controller watches the Ingress deletion and cleans up AWS resources it owns. We verified the AWS side because a Git diff or a successful Kubernetes operation alone leaves the AWS cleanup as a separate question.

**How can the app still work?** The ALB was the public entrance. The Pods and their ClusterIP Services provide the application internally. Port-forward gives an operator a temporary local connection through Kubernetes.

**What did the alert exercise demonstrate?** A confirmed SNS subscription, a CloudWatch alarm and a successful publish action were observed. The first rule used less-than-or-equal to one, so one healthy target put it into ALARM. Correcting the comparison to less-than one returned it to OK. CloudTrail exposed the exact SNS policy save errors. Inbox receipt is separate evidence from CloudWatch reporting a successful SNS action.

Start [tomorrow's read-only Python checkpoint](../next-session.md) with one Deployment snapshot and a small report.
