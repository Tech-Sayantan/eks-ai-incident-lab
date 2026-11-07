# Next session — see when the public endpoint needs attention

## Completed and verified

- Argo CD v3.6.1 is installed and Tan has used its UI.
- The orders-lab Application is Synced and Healthy after a successful manual sync.
- Both app Pods are Ready with zero restarts at closeout.
- Internal Service-name health requests returned HTTP 200.
- Java confirmed Tan's order and the payment service logged a matching successful authorization.
- Independent repeat POST and GET returned HTTP 200 for the same CONFIRMED order; the correlated payment authorization count remained one.
- Original first-create HTTP 201 was expected but not independently captured. The observed results are in study note 21.
- PR #26 switched the Application to the Helm chart. The existing Application was explicitly updated and synced.
- PR #27 added the readiness Ingress. Argo synced `b4c9008`, the ALB registered a healthy Java target on port 8080, and the Route 53 A Alias resolved to it.
- A public HTTPS request returned HTTP 200 with `{"status":"UP"}`. HTTP redirected to HTTPS with 301. See [note 24](study-notes/24-ingress-dns-and-https.md) for the failure and recovery and [note 25](study-notes/25-interview-and-troubleshooting-review.md) for the cumulative review.

## Next hands-on sequence

1. Repeat the HTTPS readiness request and view the ALB target group. The problem to solve is how to hear about loss of healthy targets without having the console open.
2. Inspect the target group's CloudWatch health metric. Choose one alarm and one SNS email subscription. Explain which resource the metric describes and how missing samples affect the alarm.
3. Confirm the email subscription and verify notification delivery with a controlled test. Record delivery evidence separately from any simulated application failure.
4. Begin the read-only Python investigator after the alert checkpoint. Use the known incident path to teach evidence collection before adding an LLM. The timeout drill remains available as a prepared scenario.

## Teaching order

Brief purpose → one small practical action → see its result → explain the fields and component interactions → diagnose a controlled failure → production tradeoffs and interview reasoning. Avoid introducing interview questions before the basic tool behavior has been observed.

## Before stopping or resuming

Local port forwards can be stopped with Ctrl+C in their respective terminals. That closes local tunnels; it does not stop EKS or delete the applications. The EKS cluster and worker continue to incur charges until teardown. The Java store is in memory, so restarting Java loses its orders and idempotency keys. Do not infer persistence from a successful rollout or HTTP response.
