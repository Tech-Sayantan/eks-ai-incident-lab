# Orders Incident Lab on EKS

A Java Orders API calls a Node.js payment simulator. The Python investigator
helps an operator explain a failed test order using live Kubernetes evidence,
a retrieved runbook, and an A2A response from a payment specialist.

The operator supplies one request ID and a question. Bedrock requests an
evidence tool. Python calls the rollout checker over MCP Streamable HTTP,
retrieves a runbook from Qdrant, and asks the payment specialist to match the
request ID in recent Pod logs. Python sends the evidence back to Bedrock and
returns the evidence alongside the explanation.

## Learn the lab

- [Beginner walkthrough and troubleshooting](docs/study-notes/27-ai-investigator-concepts.md)
- [Interview scenarios](docs/study-notes/28-ai-investigator-interview-questions.md)
- [Worked interview answers](docs/study-notes/29-ai-investigator-interview-answer-key.md)
- [Platform study notes](docs/study-notes/README.md)
- [Orders and payment API contracts](apps/README.md)

## Run the EKS demo

Use your AWS lab session and the `eks-ai-incident-lab` Kubernetes context.
From two terminals, forward the internal Services.

```bash
kubectl --context eks-ai-incident-lab -n orders-lab \
  port-forward svc/orders-api 8080:8080
```

```bash
kubectl --context eks-ai-incident-lab -n orders-lab \
  port-forward svc/orders-investigator 8082:8080
```

From a third terminal, submit a synthetic order and capture its HTTP status.
`labMode` delays the simulator, so the Orders caller should receive HTTP 504.

```bash
request_id="orders-demo-$(date +%s)"
curl -sS -o /tmp/orders-demo.json -w 'Orders HTTP %{http_code}\n' \
  http://127.0.0.1:8080/orders \
  -H 'Content-Type: application/json' \
  -H "Idempotency-Key: $request_id" \
  -H "X-Request-ID: $request_id" \
  -d '{"sku":"book","quantity":1,"labMode":"timeout"}'

sleep 4

jq -n --arg id "$request_id" \
  '{request_id:$id,question:"The Orders API returned HTTP 504. What does the payment timeout evidence show, and what should I check next?"}' |
  curl --fail-with-body --max-time 120 -sS http://127.0.0.1:8082/investigate \
    -H 'Content-Type: application/json' --data-binary @- | jq .
```

Inspect the separate `rollout`, `runbook`, and `payment` fields before
reading `answer`. A rollout can be READY while a business request fails.
The 504 is evidence from the demo curl. A payment status of 200 comes from
the simulator's own log and can be recorded after the Orders caller timed out.

## Deploy and operate

Terraform manages the investigator ECR repository, EKS Pod Identity add-on
and association, and IAM policies in its own [state root](infra/live/investigator).
GitHub Actions builds, smoke tests, scans, and publishes the Python image to
ECR. Argo CD syncs the [investigator chart](gitops/charts/orders-investigator)
from Git, using the committed image digest. The
[Application](gitops/argocd/orders-investigator.yaml) uses manual sync.

```bash
kubectl --context eks-ai-incident-lab -n argocd get application orders-investigator
kubectl --context eks-ai-incident-lab -n orders-lab get deploy,svc
```

The chart uses two Pods to fit the existing node's Pod limit. The investigator
runs separately. The MCP server, payment specialist, and Qdrant each run in
their own container in the evidence Pod. They have internal ClusterIP Services.
Qdrant uses disposable storage and recreates its index from the bundled
runbooks. Kubernetes RBAC governs the two evidence readers. Pod Identity
provides the investigator with short-lived AWS credentials for its Bedrock call.
