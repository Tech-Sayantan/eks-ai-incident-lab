# Tomorrow's first Python investigator checkpoint

Lab checkpoint verified on 7 November 2026. Argo pruned the public Ingress after PR #28. AWS confirms the ALB, target group and its network interfaces are gone. The Route 53 child zone was retired after Cloudflare's delegation disappeared and its parent TTL elapsed. The Orders and payment Pods are Ready. A local port-forward to Orders returned HTTP 200 and `{"status":"UP"}`. Read [the public endpoint closeout](study-notes/26-public-edge-retirement.md) for the DNS cleanup and state ownership.

Picture a teammate saying, “I think the Orders rollout is stuck. Can you check?” We’ll make a small Python program that reads one Deployment snapshot and answers with the numbers it saw. One snapshot and one short report are enough for the first session.

## What we’ll do together

1. Read the current Orders Deployment from the lab cluster. Use this command in your terminal when the named AWS session is active.

   ```bash
   kubectl --context eks-ai-incident-lab -n orders-lab \
     get deployment orders-api -o json > /tmp/orders-api-deployment.json
   ```

   Think of this JSON as a photo of what Kubernetes reported at that moment. If the live cluster is unavailable, we can use a small saved fixture with the same fields and label the report as a fixture.

2. Trunks supplies the small Python reader. Tan runs it against the snapshot and checks the report against the JSON. The program takes the file path and whether it came from a live snapshot or a fixture. It reads the deployment name, namespace, desired replicas, ready replicas, and the two generation numbers. The generation numbers tell us whether the controller has processed the latest specification.

3. Read the result aloud. An example for a current snapshot might be `orders-lab/orders-api | READY | 1 of 1 replicas ready | generation 4 observed as 4`. The exact generation comes from your file. If the controller has processed the current spec and fewer Pods are ready than requested, the report says `NOT_READY`. If the snapshot cannot answer the question, it says `UNKNOWN` and explains what information is missing or stale. Zero desired replicas is a separate `SCALED_DOWN` result.

The program reads a file. The live collection step reads a Kubernetes object. Giving an investigator read access lets it show a human the evidence while keeping rollout decisions with the operator. The public domain and ALB are outside this evidence path. A later independent HTTP check can use a temporary local port-forward to the Orders Service.

## If you get stuck

If `kubectl` says `Unauthorized`, first check your named AWS session and the `eks-ai-incident-lab` context. Refresh the lab login if it expired, then repeat the read. A failed read means we have no fresh evidence about the app. It should produce `UNKNOWN`, since an access error says something about our connection and permissions. A fixture gives us a way to practise the Python part while we resolve live access.

## Interview practice after seeing the report

**“The report says one of one Pods is ready. Does that prove checkout works?”** It proves the Deployment reported a ready replica for the current generation. Checkout also calls the payment service. I would run a request through the Orders API and trace its request ID through both services to verify that path.

**“Why did you make the investigator read-only?”** It can help an operator explain a symptom without having permission to restart or modify a production service. I would keep its permission scoped to the evidence it needs, report uncertainty explicitly, and leave changes to the reviewed deployment process.

Once the evidence reader works, Bedrock can help explain the collected evidence in plain language. RAG can add the relevant runbook. MCP can expose the same evidence reader as a tool. A2A comes later if we want a separate specialist investigator to collaborate. For this checkpoint, the result comes from Python reading the snapshot.
