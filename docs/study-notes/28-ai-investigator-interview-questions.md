# Orders investigator interview questions

Try each aloud before opening the answer key. Start with the first check you would make, the result you expect, and what would make you change direction. Use the Orders incident when an interviewer asks for a concrete example.

## Explain the project

1. In a minute, explain what happens when on-call asks the Orders investigator why checkout is failing. Where does Python run, where does the model run, and which component collects evidence?
2. The Deployment says `desired=1 updated=1 available=1`. What can you say confidently, and what would you check before declaring checkout healthy?
3. Why keep the rollout classification in Python if Bedrock can read the Kubernetes JSON? Which decisions can the model make and which ones belong to code?

## Follow a tool call and a delegated investigation

4. Trace one rollout tool call from the question through the final Bedrock reply. Where does the tool call ID matter?
5. The same tool works locally over stdio and fails after the switch to Streamable HTTP. What changed, and how would you isolate the first failing hop?
6. MCP discovery shows `orders_rollout`, but the tool returns a Kubernetes forbidden error. What did discovery prove? What access would you grant, and to whom?
7. Your team can expose the Payments investigator as a tool. What would make you choose A2A for it? Explain an Agent Card, task, and artifact using one checkout example.
8. The Payments agent cannot find the request ID. What should the Orders answer say? How would you improve the evidence on the next investigation?
9. A user asks the investigator to delete the bad Pod immediately. How do you make sure the current read-only system stays read-only, even if the model asks for a mutation?

## Retrieval, deployment, and reliability

10. Walk through how “checkout hangs” can retrieve a runbook named “payment dependency timeout.” Explain chunks, embeddings, vectors, Qdrant, and generation.
11. The investigator cites an old runbook and recommends the wrong step. How do you find whether the fault is in retrieval or generation, and how would you prevent a repeat?
12. Bedrock responds with access denied in one test and a daily token throttle in another. What do you check for each, and how should the investigator behave if generation is unavailable?
13. The MCP Pod can read a Deployment, but the investigator Pod cannot invoke Bedrock. Explain Kubernetes RBAC, EKS Pod Identity, and IAM. Where does image pull access fit?
14. GitHub Actions published a new image and Argo is green. A teammate insists the old code is running. What evidence settles it? How would you roll back a bad release in GitOps?
15. The business wants the investigator hosted but says to keep the demo inexpensive. Describe the network boundary, what continues accruing cost, and how you demonstrate the lab safely.
16. You are asked whether to trust this in on-call rotation. Propose a small evaluation set and explain what you would measure before recommending it to the team.

[Open the answer key](29-ai-investigator-interview-answer-key.md)
