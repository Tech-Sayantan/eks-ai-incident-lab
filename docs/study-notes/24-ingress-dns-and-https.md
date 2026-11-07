# 24 — Follow one HTTPS request to the Orders API

Verified on 7 November 2026. The AWS Load Balancer Controller v3.6.2 Deployment is Ready at 1/1, its ServiceAccount is annotated with the lab IAM role, and the `alb` IngressClass exists. ACM shows the certificate for `orders.tanscape.online` as ISSUED in Mumbai. Cloudflare delegates that hostname's zone to Route 53.

When Tan ran `kubectl get ingress orders-api`, Kubernetes returned `NotFound`. PR #27 was open with all four checks passing. Argo was green on the older commit on `main`, so it had never received the Ingress. Trunks squash-merged the checked PR and requested an Argo sync of `b4c9008`. Argo reported Synced, Healthy and Succeeded. The controller then filled in the Ingress address and AWS registered the Java Pod on port 8080 as a healthy IP target.

The port 443 listener has the issued ACM certificate and the port 80 listener redirects to HTTPS. Trunks checked HTTPS against the ALB first, keeping the public hostname for certificate verification, then created the A Alias in the Route 53 child zone. A normal public DNS request to the readiness URL returned HTTP 200 with `{"status":"UP"}`. Plain HTTP returned 301 to the HTTPS URL. The checked public route is the readiness endpoint.

Imagine opening `https://orders.tanscape.online/actuator/health/readiness` on your phone. It first needs an IP address to connect to. Public DNS reaches Cloudflare, which refers lookups for this subdomain to Route 53. The Route 53 A Alias answers with the ALB's addresses. Your phone connects to one of those addresses on port 443.

Your phone asks for the certificate for `orders.tanscape.online` during the TLS handshake. The ALB presents the certificate ACM issued. The browser checks its name and trust chain. Once HTTPS is established, the ALB can inspect the HTTP hostname and path and apply its rule. With IP targets, the ALB forwards HTTP to a registered Java Pod on port 8080. The Kubernetes Service identifies the backend endpoints. The controller uses those endpoints when managing targets.

The steps that build this path happen before anyone can use it.

1. Argo syncs an Ingress object from our chart. Its class is `alb`, and it names a hostname, path, Service and port.
2. AWS Load Balancer Controller sees the object and calls AWS with its IAM role. AWS creates the ALB, listeners, rule and target group. The controller writes the resulting DNS hostname into the Ingress status.
3. The certificate ARN in the Ingress tells the controller which ACM certificate to attach to the HTTPS listener.
4. We create an A Alias in the Route 53 zone for `orders.tanscape.online` and select that ALB. An empty record-name box represents the zone's own name.
5. A request to the hostname now tests the entire path.

The ACM validation CNAME is the proof that you control the domain. The A Alias is the answer for where browser requests should go. Keep the validation CNAME available for ACM renewal while the certificate is in use.

## Read the Ingress from top to bottom

- `ingressClassName: alb` selects the controller that will implement this request.
- `scheme: internet-facing` gives the ALB a public entry point. Our two public subnets have the AWS discovery tag.
- `target-type: ip` registers Java Pod IPs. The Service remains ClusterIP and identifies the backend by port and endpoints.
- `listen-ports` opens HTTP 80 and HTTPS 443. `ssl-redirect` makes the HTTP listener send the client to HTTPS.
- `certificate-arn` selects our issued ACM certificate. `ssl-policy` permits TLS 1.2 and 1.3.
- `backend-protocol: HTTP` makes the ALB-to-Java connection use HTTP. Browser-to-ALB HTTPS ends at the ALB.
- `healthcheck-path` is where the ALB asks Java whether it can serve. The ALB does this independently of the kubelet readiness check.
- The exact listener path exposes the readiness endpoint for this first public lab check. Checkout can still be tested using the existing local tunnel.

The controller uses Kubernetes and AWS APIs to build and maintain these settings. The ALB serves the browser request. The controller can be restarted without becoming a hop on the request path.

## How to find the failing layer

| What you observe | What to check first | How to fix the indicated cause |
|---|---|---|
| Ingress Address remains empty | `kubectl describe ingress`, IngressClass, controller logs | Correct class, missing IAM action, subnet tags or certificate configuration indicated by the error |
| Address exists but the hostname doesn't resolve | Check the public Route 53 child zone, NS delegation and the A Alias | Create the Alias at the child-zone apex using the correct ALB |
| Browser warns that the name on the certificate is wrong | Confirm the URL, listener 443 certificate and ACM domain | Use the lab hostname and attach the matching issued certificate in Mumbai |
| ALB returns 404 | Check the listener's host and path rule | Send the expected hostname and exact path or change the reviewed Ingress rule |
| Target group reports unhealthy targets | Check target-health reason, Pod endpoints, port, health path and backend security-group rules | Correct the specific port, path, readiness or connectivity failure |
| ALB returns 503 | Check whether it has usable registered targets and the matching forward rule | Restore correct endpoint registration and verify targets and listener action |

Compare the health checks separately. Kubelet readiness is about whether Kubernetes marks the Pod ready. ALB health is about whether the ALB can reach and successfully check that target. The endpoint can be the same, while network access and callers differ.

## Questions that come up in interviews

**Does applying Ingress always create an ALB?** Kubernetes stores the rule. Our AWS controller reads the `alb` class and provisions the AWS resources when its IAM, networking and Ingress inputs are valid. Other controllers implement Ingress in different ways.

**Why does the backend Service still use ClusterIP?** In IP mode the controller uses the Service's endpoints to register Pod IPs. The ALB can send traffic directly to those targets. The Service describes which Pods and port belong to the backend.

**Why can't we set the Alias before the Ingress sync?** We need the particular ALB created by this Ingress. Its generated hostname appears in status once the controller provisions it. A DNS record alone cannot create a load balancer.

**Where is HTTPS terminated?** The ALB's port 443 listener presents the ACM certificate and terminates the browser's TLS connection. It then forwards to Java over HTTP in our setup. For end-to-end encryption, we would configure HTTPS on the backend too.

**Why can a Ready Pod be unhealthy in the target group?** The kubelet and the load balancer probe from different places. Check target health reason and ALB-to-Pod connectivity, health check port, path and expected status.

**Why is an ALB address in Ingress status different from the app URL?** The ALB's DNS name identifies the AWS endpoint. The public URL has the name on our certificate and in the host rule. The Alias connects those two names through DNS.

**What if someone edits the listener directly in the AWS console?** The controller owns the AWS configuration described by the Ingress and may reconcile that edit away. Make a durable listener change through the reviewed Ingress configuration.

## Lab cost

AWS's Mumbai on-demand list price checked on 7 November 2026 was $0.0239 per ALB hour and $0.008 per used LCU hour. With two public IPv4 addresses at $0.005 per address-hour, an ALB adds about $0.81 per 24 hours before usage, transfer or tax. Existing EKS and Route 53 costs are separate.

- [AWS Load Balancer Controller v3.6.2 annotations](https://raw.githubusercontent.com/kubernetes-sigs/aws-load-balancer-controller/v3.6.2/docs/guide/ingress/annotations.md)
- [Amazon EKS ALB routing](https://docs.aws.amazon.com/eks/latest/userguide/alb-ingress.html)
- [Route 53 Alias to an ALB](https://docs.aws.amazon.com/Route53/latest/DeveloperGuide/routing-to-elb-load-balancer.html)
- [AWS Mumbai load balancing price list](https://pricing.us-east-1.amazonaws.com/offers/v1.0/aws/AWSELB/current/ap-south-1/index.json)
- [Public IPv4 pricing](https://aws.amazon.com/vpc/pricing/)
