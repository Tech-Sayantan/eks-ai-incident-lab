# The Orders incident investigator, from the first question to EKS

Start with a support ticket. A customer says checkout stalled. On-call asks, “Did Orders finish deploying, and what should I check next?” Those are two different questions. Kubernetes can report on the Deployment. The team’s runbook explains what evidence to look for next. The investigator gathers those pieces and helps you decide where to look.

Follow the question through the deployed design.

```text
On-call question
  → Orders investigator (Python)
      → MCP rollout tool → Kubernetes Deployment
      → Qdrant → relevant runbook passage
      → Payments specialist over A2A, when a request ID is supplied
      → Bedrock → evidence-based reply
```

One example from our lab is `READY | desired=1 total=1 updated=1 available=1`. Kubernetes observed one requested replica, one replica matching the current Pod template, and one available replica in the snapshot. That still leaves the customer’s checkout path to verify. For this lab, a deliberate test order uses `sku`, `quantity`, and an `Idempotency-Key`. A fresh successful order returns HTTP 201 and `CONFIRMED`. It creates an order, so a person should choose an appropriate test environment and control when to run it.

## Python, Bedrock, and the model

Picture the first Python script as a checklist you taught a computer to follow. It loads a saved Kubernetes snapshot, reads fields such as `updatedReplicas`, and applies rollout rules. Give it the same snapshot twice and you get the same result. That is useful when another person needs to reproduce your finding.

**Amazon Bedrock** is the AWS service we call over an API. It authenticates the caller, makes the selected model available through an endpoint, and returns the model’s response. **GPT OSS 20B** is the model we ask to interpret the evidence. Our early lab called the Bedrock Mantle endpoint with an OpenAI-compatible API. “OpenAI-compatible” describes the request format here. The endpoint and credentials belong to AWS. [Amazon Bedrock endpoints](https://docs.aws.amazon.com/bedrock/latest/userguide/endpoints.html)

The **agent** is our Python application when it runs the investigation loop. It decides what capabilities to advertise, accepts or rejects the model’s tool requests, calls approved tools, and returns the result to the model. Python dictionaries hold structured fields such as the tool name and arguments. A Python function executes the approved operation. The MCP SDK handles protocol messages and the model client handles API calls. An agent framework can package orchestration, but the underlying loop is still ordinary application logic. We can understand this one by tracing a single tool call.

## What a tool call actually does

Suppose you ask, “Is the Orders API rollout ready?” Python sends the question to Bedrock alongside a tool description for `orders_rollout`. A tool description tells the model what the tool does and which arguments it accepts. Here, the tool has a fixed target, so the model has no need to choose a cluster, namespace, or shell command.

| Hop | What you would see |
| --- | --- |
| Python → Bedrock | The question and a description of the allowed tool |
| Bedrock → Python | A structured request for `orders_rollout`, with a call ID |
| Python → MCP server | A validated call for that named tool |
| MCP server → Python | The checker’s rollout evidence |
| Python → Bedrock | The tool result paired with the original model call ID |
| Bedrock → Python | An explanation of what the evidence supports and a suggested next check |

To connect the earlier practice files to this flow, start with `check_rollout.py` for the checker, then `ask_bedrock.py` for the first model call. `rollout_tool_call.py` lets you see the request-and-result loop in one process. `orders_mcp_server.py` publishes the checker as an MCP tool and `orders_mcp_client.py` calls it across that protocol. Those exercises build toward the hosted investigator.

The model can suggest a tool call. The application owns execution, input checks, timeouts, and the maximum number of calls. If the tool fails, the agent should expose the missing evidence and avoid inventing a result. The model’s call ID pairs a tool response with a particular request. A customer request ID is a different identifier used to correlate application logs.

## MCP and its two transports

**Model Context Protocol (MCP)** gives an AI application a common way to ask a tool server what tools it offers and call one of them. In the lab, the client discovers `orders_rollout`, then sends a call. The server maps that name to our Python checker and returns the result. Discovery tells you the client reached the server and can see the tool. A successful call tells you the checker ran. The checker’s configured data source tells you whether that result represents a saved example or the live cluster.

**Transport** means how the messages travel. The checker can run the same Python function over either transport.

| | stdio | Streamable HTTP |
| --- | --- | --- |
| How the message travels | The client starts a local subprocess and writes messages to its standard input. The server replies on standard output. | The client sends MCP requests over HTTP to an endpoint such as `/mcp`. The server can reply with JSON or stream events when needed. |
| Who keeps the server running | The launching client owns the subprocess. | The server runs independently. In EKS, Kubernetes runs the Pod and a Service supplies a stable address for callers. |
| What to check first | Executable, working directory, and unexpected text on standard output. Send debugging logs to standard error. | Server address, port, path, and protocol response. Then check Service endpoints and network access. |

In “Streamable HTTP,” a **stream** lets the server deliver events as they become available on the response. A quick rollout answer can come back in one response. The transport still works when the operation has no updates to stream. For the lab, the endpoint can be reached by in-cluster callers. A developer can use Kubernetes port-forwarding for a temporary local demo without paying for a public load balancer. Use an MCP client to test discovery and invocation because an ordinary browser request tests a different operation. [MCP transports](https://modelcontextprotocol.io/specification/latest/basic/transports)

## When MCP is enough and when A2A makes sense

If the investigator needs a rollout number, that is a small, bounded operation. It can call an MCP tool and use the returned evidence in the same answer. Wrapping an agent as an MCP tool can also be a reasonable interface when callers only need one request and one result.

Now imagine Payments has its own investigator and team. Orders says, “For this test request ID, can you investigate the payment side and send back your findings?” Payments owns how it gathers evidence. An A2A client can discover its **Agent Card**, a published description of the agent’s interface and skills. It can send a **message**, and the peer can return a quick reply or a **task** with an identity and status. A task can represent work that is still in progress or needs more input. An **artifact** is an output the peer produces, such as a findings report. The agent card helps discovery, while authentication and authorization still govern who can invoke the agent. [A2A key concepts](https://a2a-protocol.org/latest/topics/key-concepts/)

Use the same checkout incident to see where the two fit. Orders can use MCP to get rollout evidence. It can delegate a payment investigation over A2A when the question calls for that separately owned capability. Payments might use its own tools to check logs. The Orders agent should say when no matching evidence was found and avoid attributing the failure to Payments merely because it made the request. [A2A and MCP](https://a2a-protocol.org/latest/topics/a2a-and-mcp/)

## Embeddings, vectors, Qdrant, and RAG

Take two phrases, “checkout hangs waiting for payment” and “payment dependency timeout.” Exact-word search might miss the second if you type the first. An **embedding model** maps each phrase to a list of numbers that can place related phrases near one another. That list is a **vector**. An individual number usually has no useful label such as “payment.” The relationship comes from comparing whole vectors. Similarity is a ranking signal, so a highly ranked runbook can still be wrong for a particular incident.

**Qdrant** stores the vectors alongside the original text and metadata such as a source name. In the lab we use the same compatible embedding model for runbook passages and questions. A query asks Qdrant for nearby vectors and returns their associated text. Cosine similarity measures how closely two vectors point in the same direction. The early exercise uses Qdrant client local mode, which stores data on disk without operating a separate Qdrant server. The EKS design gives Qdrant an internal Service and uses temporary Pod storage. Runbook vectors can be rebuilt from the bundled passages when that Pod is replaced. If the index becomes a shared service, plan its storage, backups, and restore test. [Qdrant local mode](https://github.com/qdrant/qdrant-client#local-mode) · [Qdrant FastEmbed guide](https://qdrant.tech/documentation/tutorials-basics/generate-embeddings-fastembed/)

**RAG** means retrieval-augmented generation. Retrieval finds passages. Generation uses those passages as context to write an answer.

1. Break trusted runbooks into useful passages. Keep a source label with each passage.
2. Embed the passages and index them in Qdrant.
3. Embed “Checkout returned 504 after a release” and retrieve the most relevant passages.
4. Give Bedrock the question, the retrieved text, and the rollout evidence we actually collected.
5. Return a suggested check with its source. If the passage is weak or absent, say which evidence would narrow the incident.

The embedding model helps find text. The generative model explains it. The runbook provides procedural advice, while the checker gives incident evidence. A runbook saying “a timeout can be caused by Payments” is a hypothesis to test. A matching timeout log for this request is evidence you can investigate. Retrieval changes what the model sees for this request. Publishing a runbook update therefore means refreshing the index, without retraining the generation model. [How retrieval and generation fit together](https://docs.aws.amazon.com/bedrock/latest/userguide/kb-how-it-works.html)

## What EKS adds to the lab

When the AI components are deployed, your laptop becomes one possible client. An image contains Python, the application, and its dependencies. ECR stores the image. Kubernetes starts it as a Pod, and a Service gives the running endpoint a stable DNS name. Helm renders the resource definitions from templates and values. Argo CD watches the desired Git revision and reconciles those resources. This gives you different places to inspect for build, publish, deploy, and runtime failures.

The lab node has room for two new Pods. The investigator runs in one. The other runs the MCP server, Payments specialist, and Qdrant in three containers with three different Service ports. They share a Pod lifecycle. If one of those containers fails readiness, all three Services can lose their ready endpoint. Both Deployments use the `Recreate` strategy so an update fits the node's available Pod slots. Expect a short interruption during replacement.

The model continues to run in Bedrock. The application in EKS sends the model request and connects the response to the rest of the investigation. Two permissions matter here.

| If this process needs to… | Give it… | Where to look when access fails |
| --- | --- | --- |
| Read a Kubernetes Deployment or approved Pod logs | A Kubernetes ServiceAccount and narrowly scoped RBAC for the needed Kubernetes verbs and resources | Kubernetes error, Role/RoleBinding, namespace, and identity |
| Invoke an AWS model | Temporary AWS credentials through an EKS Pod Identity association and an IAM role with the required Bedrock permissions | Pod Identity Agent, association and service account, SDK credential source, IAM policy, endpoint and model access |

The **EKS Pod Identity Agent** runs on eligible worker nodes. In plain terms, a Pod with the appropriate association can ask the agent for short-lived AWS credentials. The AWS SDK discovers the credential endpoint and uses the temporary credentials to sign AWS requests. The role controls what the Pod can do in AWS. Kubernetes RBAC independently controls what a ServiceAccount can do to Kubernetes objects. The two evidence readers share the `orders-evidence` ServiceAccount and mount its projected token. The Qdrant container has no mount for that token. Separating the readers into their own Pods would let you give each a different identity and rollout schedule. There is also an image pull step before the app starts. For an EKS managed node group, the node’s ECR access is typically what matters at that step. [How EKS Pod Identity works](https://docs.aws.amazon.com/eks/latest/userguide/pod-id-how-it-works.html) · [Kubernetes RBAC](https://kubernetes.io/docs/reference/access-authn-authz/rbac/)

## A short way to debug the demo

Read the incident from left to right and stop at the first missing piece.

- **No ready agent Pod.** Check the Argo revision, Pod events, image tag, image pull permissions, and startup logs. A Deployment can be created even when its container fails to start.
- **Agent runs, but MCP discovery fails.** Check service DNS, port, `/mcp` path, ready endpoints, and server binding. A process bound to loopback accepts connections from inside its own Pod.
- **MCP discovery works, but the tool fails.** Look at tool execution logs and the target Deployment. Check whether the checker is using a saved fixture or Kubernetes and whether its ServiceAccount can read the object.
- **Tool returns evidence, but Bedrock fails.** Check the exact service response. Access errors can point to credentials, IAM, or account-level model access. A daily token quota error calls for checking the effective quota and usage for the model and region. Short retry backoff serves transient throttling.
- **RAG returns the wrong runbook.** Read the top retrieved text, its score, and its source. Look for stale or overly large passages and incompatible indexing/query encoders. Fix retrieval and test the same query before changing the generation prompt.
- **Payments has no matching entry.** Verify the request ID, time window, workload selection, and log retention. Report what you searched and which part remains unknown.
- **Everything is green and a customer still sees failures.** Follow a controlled request from the client to the order response, then correlate application logs by request ID. Compare what passed at rollout time with what the transaction actually exercised.

A practical interview exercise is to walk through two paths aloud. First use a ready snapshot and say what remains unknown. Then imagine a new rollout with zero available replicas and use Pod events to narrow your next check before suggesting any fix.
