# Adopt the Orders hostname

This root manages four objects already created for the lab: the public `orders.tanscape.online` hosted zone, the issued ACM certificate, the DNS validation CNAME, and the A Alias. The state key is `eks-ai-incident-lab/edge/terraform.tfstate` in the existing encrypted lab bucket.

The import blocks map each Terraform address to its real AWS ID. The first plan should report four imports and zero additions, changes, or destroys. Subsequent plans should show no changes.

```bash
aws sts get-caller-identity --profile eks-ai-incident-lab
AWS_PROFILE=eks-ai-incident-lab terraform -chdir=infra/live/edge init \
  -backend-config=profile=eks-ai-incident-lab
AWS_PROFILE=eks-ai-incident-lab terraform -chdir=infra/live/edge plan \
  -out=adopt-edge.tfplan
terraform -chdir=infra/live/edge show adopt-edge.tfplan
```

The ALB belongs to the AWS Load Balancer Controller. This state holds its DNS name only as the Alias target. If the controller recreates the ALB, update the Alias target in this configuration. Cloudflare manages the parent delegation separately. Route 53 creates the child zone's default NS and SOA automatically.

Plan teardown separately. Retire the public route and remove the Ingress through Git and Argo so the controller deletes the ALB. Remove the four lab delegation records in Cloudflare before deleting the child hosted zone. Confirm the certificate is detached from any listeners before deleting it. The EKS, ECR, network, and backend resources live in their own Terraform roots.
