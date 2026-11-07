# EKS interview review — start with what you saw in the lab

When an interviewer describes a failure, picture a real request or change moving through the system. Identify the last step you can prove worked. The next step is usually where you’ll find the evidence.

## 1. Terraform, S3 and state

**Why did you create a bucket before setting up the S3 backend?** Terraform needs somewhere to write state before it can use the remote backend. We created that foundation first and migrated the existing state into S3. Terraform still manages the bucket because the state maps its resource address to its AWS ID. Changing where the record lives does not change the bucket.

**Could one AWS account have more than one state file?** Yes. Our bootstrap and lab use separate state keys. Bootstrap holds shared setup such as the backend and GitHub identity. The lab holds the network and EKS resources. Different projects can have their own state and share infrastructure through IDs or outputs. Give each AWS resource a single Terraform owner.

**What if Terraform says the state is locked?** Check whether another apply is still active. Two applies working on the same state can race. If the original run is genuinely gone, verify that before removing its stale lock. If a run failed halfway through, inspect state and the AWS resources, then produce a fresh plan. Some resources may already exist.

**Why review a saved plan?** A plan shows what Terraform intends to change at a particular point. Applying the same saved plan means the guard and approval refer to the same operations. After apply, check the AWS API to confirm the result.

Revisit [bootstrap and state](01-terraform-bootstrap-and-oidc.md), [Terraform CI and Trivy](02-terraform-ci-and-trivy.md), [network apply verification](08-network-apply-and-verification.md) and [partial apply recovery](12-eks-partial-apply-recovery.md).

## 2. GitHub Actions, IAM and Git

**What does OIDC do for GitHub Actions?** GitHub gives the job a signed token saying which workflow context it came from. AWS STS checks that token against the role’s trust policy and returns temporary credentials. The trust policy controls who can assume the role. The permissions policy controls what that role can do afterward.

**Why have separate plan, apply and image-publishing roles?** Each job needs different permissions. A plan job needs state access and enough AWS read permissions to inspect resources. An apply job needs the approved infrastructure writes. Publishing images needs ECR permissions. Narrow roles limit the impact of a mistake or compromised job.

**How do you debug AccessDenied?** Find the exact API and caller in the error. If STS cannot assume the role, check the OIDC issuer, audience, repository or branch subject, and trust policy. If role assumption succeeded and an AWS API failed later, inspect the role’s permissions, resource ARN and conditions for that action.

**Checks passed. Who approved it?** In this lab the checks prove that automated jobs succeeded. An independent human review is a separate gate when configured. Merge puts the change on the branch Argo watches. An environment approval, when used, gates the deployment job separately.

**What’s squash merge? What about a merge conflict or cherry-pick?** Squash combines the PR changes into a single commit on the target branch. A conflict asks you to decide which edits to keep when Git can’t combine them safely. Cherry-pick applies one selected commit’s change to your current branch. If you want to see what will enter your next commit, use `git diff --staged`.

Revisit [PRs and approvals](04-pr-ci-cd-and-approvals.md), [OIDC plan role](05-oidc-plan-role.md), [network plan and Git](06-network-cloud-plan-and-git.md), [apply role and gates](07-apply-role-and-merge-gates.md) and [image-publisher OIDC](17-image-publisher-oidc.md).

## 3. VPC, EKS and add-ons

**What makes a subnet public?** A VPC is scoped to a region and a subnet lives in one Availability Zone. A public subnet’s route table has a route to an Internet Gateway. A workload still needs an appropriate address and a security-group rule for traffic to reach it. A private subnet can use NAT for outbound internet access without making the workload directly reachable from the internet.

**Security group or NACL?** A security group is a stateful firewall for a network interface. Reply traffic to an allowed connection is tracked. A network ACL applies to the subnet and evaluates each direction separately. If a NACL blocks return ports, the incoming rule can look correct while the connection still fails.

**What does EKS manage, and why the three add-ons?** EKS manages the control plane. Our managed node group provides the worker machines. VPC CNI gives Pods VPC networking, CoreDNS resolves Kubernetes names, and kube-proxy helps implement Service forwarding. That gives you a useful starting point for debugging a Pod IP, DNS or Service problem.

**How would you debug kubectl access?** A connection timeout points first to DNS or reachability. An authentication error points to the AWS identity in kubeconfig and the EKS access entry. An authorization error points to permissions for the requested action. Check the layer the error actually names.

Revisit [VPC foundations](03-vpc-networking-foundations.md), [network apply](08-network-apply-and-verification.md), [EKS add-ons](09-eks-addons.md), [EKS IAM](10-eks-iam-bootstrap-apply.md) and [EKS API access](11-eks-api-access-for-poc.md).

## 4. Application CI, Docker and ECR

**Why does Java return 504 if both Pods look healthy?** Java waits 1.5 seconds for payment. The timeout fixture makes Node wait three seconds. Java can therefore give up while both readiness endpoints stay green. Follow the request ID across the two services and compare the times. In a real payment system, a timeout can leave the payment outcome uncertain. Check the provider’s result and idempotency contract before retrying.

**What did CI verify before publishing?** Maven builds and tests Java and runs Checkstyle. Node installs locked dependencies and runs its tests. Docker builds the images, and the publication workflow checks the images before pushing. A runtime smoke test adds evidence about discovery, configuration, startup and application behavior.

**What does a multi-stage Dockerfile buy us?** One stage can compile or install build dependencies. The final stage carries the files and runtime dependencies the app actually needs. Image size is disk and transfer size. CPU and memory at runtime are governed by the container environment and Kubernetes requests and limits.

**Why pin an image digest?** The digest identifies the built content. Git can record exactly what passed checks and what should run. If a Pod has `ImagePullBackOff`, check the image reference and registry path, then the node’s pull permissions and network access. The runner’s ability to push an image is a separate permission.

**Can you scale the Java app safely just by changing replicas?** Today each Java process has its own order and idempotency store. Two replicas can disagree about whether an order exists. To scale safely, design shared durable storage and preserve the retry contract across replicas and restarts.

Revisit [app foundations](13-application-foundations.md), [Docker images](14-docker-images.md), [ECR and IAM](15-ecr-repositories-and-iam.md), [guarded ECR apply](16-guarded-ecr-apply.md), [image-publisher trust](17-image-publisher-oidc.md), [image publishing](18-image-publishing.md) and the [timeout case](22-payment-timeout-investigation.md).

## 5. Kubernetes, Helm and Argo CD

**How do Deployment and Service fit together?** The Deployment owns a Pod template and asks its ReplicaSet to maintain replicas. The Service gives callers a stable name and finds Pods through labels. If a Service has zero usable endpoints, compare its selector with the Pod labels and readiness before investigating the network.

**What do the three probes tell you?** Startup gives a slow app time to come up. Liveness can trigger a container restart. Readiness determines whether the Pod should receive traffic. A whole business transaction still deserves its own check.

**Why use Helm here?** A chart combines templates and values to produce Kubernetes manifests. Our values pin images and define payment configuration. Argo renders the chart and owns sync, so Git and Argo show the deployment history. A chart rendered by Argo does not create an ordinary Helm CLI release.

**Why did the checksum restart Java?** Java receives environment variables at startup. A changed ConfigMap leaves the existing process with the old environment. We hash the configuration and place the result in the Pod template. When that hash changes, Kubernetes replaces the Pod and the new process gets the new values.

**What does dry run prove?** It exercises the rendering or API checks you actually ran. A local Helm render proves that values produce YAML. A server-side dry run asks the API to evaluate the resources without persisting them. Pod scheduling, image pulls, probes, traffic and a business request are later checks.

**Why can CI be green and Argo be green while my Ingress is missing?** CI tested the PR branch. Argo compared the cluster with its tracked revision on `main`. If the PR is still open, the two green screens describe different inputs. Check the merge, refresh Argo and inspect the diff before syncing.

**What do auto-sync, self-heal and prune do?** Auto-sync can apply a newly observed desired change. With automated sync enabled, self-heal can restore a tracked field someone edited live. Prune can delete tracked resources removed from the desired manifests. If someone deletes one Pod from a Deployment, the ReplicaSet normally replaces it.

**How would you undo a release?** Restore the working digest or configuration in Git, review it, sync and test. For a manually synced application, Argo’s history can also help restore a previous deployment. Git still needs to reflect the intended version. A deployment rollback cannot reverse a database migration or payment by itself.

**Where are the canary and blue-green controls?** Argo CD delivers the manifest. Argo Rollouts is the controller that runs the release strategy written in a `Rollout` object. Blue-green gives you a preview version before promotion. Canary gives the new version a share of requests and pauses for evaluation. A traffic router such as an ALB can apply deliberate weights. Rollouts remains a future POC for this lab.

Revisit [Kubernetes resources and dry run](19-kubernetes-resources-and-dry-run.md), [Argo bootstrap and interview guide](20-argocd-bootstrap-and-interview-guide.md), [first Argo sync and HTTP](21-first-argo-sync-and-http.md) and the [Helm guide and its 12 scenarios](23-helm-conversion.md).

## 6. Route 53, ACM, Ingress and the ALB

**If DNS returns an address, does that prove HTTPS works?** DNS tells your browser where to connect. TLS then checks the certificate presented for the hostname. Only after that can the ALB inspect the HTTP request and choose a backend. You can test and troubleshoot each part separately.

**What was the difference between the two DNS records?** The validation CNAME is the proof ACM checks to issue and later renew the certificate. The A Alias is the answer your browser gets when it asks where the app lives. Cloudflare delegates only `orders.tanscape.online` to the Route 53 child zone. The Alias belongs at that child zone’s root, so the Route 53 record-name box is blank.

**What actually creates the ALB?** Argo syncs the Ingress into Kubernetes. The AWS controller sees its `alb` class, uses its IAM role to create AWS resources, attaches ACM’s certificate to listener 443, and writes the resulting hostname into Ingress status. With IP targets, the Service identifies backend endpoints and the ALB forwards directly to the Java Pod IP on 8080.

**How do you diagnose the exact failure?**

- **Ingress returns NotFound.** Check Git and Argo first. Did the change merge into the tracked branch, and did Argo sync that revision?
- **Ingress exists with an empty Address.** Read its Events and controller logs. Look for an IAM, subnet, certificate or Ingress class error. Fix the specific cause before trying another sync.
- **The URL cannot resolve.** Query the hostname with `dig`. Check the child zone delegation and its A Alias. An issued certificate alone leaves the browser without a destination.
- **TLS fails with a name mismatch.** Use the public hostname in the request and check listener 443 for the matching issued certificate in the ALB’s region.
- **ALB returns 404 or the targets look unhealthy.** A default ALB 404 can point to the host or path rule. For a failing target health check, inspect its reason, Pod endpoints, health path, port and security groups. The kubelet can reach a Pod while the ALB cannot.

**What evidence closes the deployment?** Capture the Git revision, Ingress address, target health, DNS answer and one real HTTPS response. For PR #27, the checked chain was `b4c9008` synced by Argo, a populated Ingress address, a healthy Java IP target on 8080, an A Alias and HTTP 200 with `{"status":"UP"}`. The readiness request proves the public path. Checkout and the later timeout case give separate business evidence.

Revisit [Ingress, DNS and HTTPS](24-ingress-dns-and-https.md). The [study-note index](README.md) links every checkpoint and its original question set.
