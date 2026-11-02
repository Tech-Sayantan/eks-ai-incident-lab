# 14 — Docker images: Java and Node.js

## The mental model

A Dockerfile is a recipe. `docker build` executes it using a **build context** (the directory at the end of the command) and produces an image. `docker run` creates a container from that image. The image contains read-only layers and startup configuration; the container is a running process plus its writable layer. Rebuild the image and replace the container to deploy a change. An image tag is a mutable name; a digest identifies specific image content.

Our build contexts are `apps/orders-api` and `apps/payment-simulator`. `COPY` cannot read outside its context. Each directory has a `.dockerignore` to keep local output and dependencies out of the context.

## Why these files look different

The Java image uses two stages. The `maven:3.9-eclipse-temurin-21` stage compiles, tests, and checks style with `mvn verify`. The final `eclipse-temurin:21-jre-noble` stage receives only the runnable JAR, so Maven, source, and test tools do not ship in the runtime image. The JAR name must match the artifact in `pom.xml`. UID `10001` runs the service without root privileges.

The original Node image used one stage because the app is plain JavaScript and has no compilation or bundled frontend assets. The revised image has a `deps` stage that installs production dependencies and a `runtime` stage that copies only `node_modules`, `package.json`, and source files. This excludes the install stage's npm cache from the final filesystem. Both stages use the same Node base, so the runtime still contains npm; the size gain is modest. For TypeScript or frontend builds the stage boundary also keeps compilers and intermediate build files out of the runtime image. A manifest change invalidates the dependency layer; a source-only change can reuse it. The Java Dockerfile does not currently have a separate dependency-install layer, so a source change reruns `mvn verify` inside the image build.

The Node runtime must copy `package.json`: its `"type": "module"` setting tells Node to interpret this app's `.js` files as ES modules. Omitting it can make the container build successfully but fail at startup on `import` syntax.

`RUN` executes during image build. `CMD` supplies a replaceable startup default; `ENTRYPOINT` supplies the main executable. `EXPOSE` documents the container port; `docker run -p 8080:8080` would publish it on a host. Java uses exec-form `ENTRYPOINT`; Node uses exec-form `CMD`. `USER` sets the runtime identity. Kubernetes will later own restart and readiness behavior; `EXPOSE` itself does not create a health check.

## Four different resource questions

1. **Image size on disk:** JRE/Node base layers, app files, and dependencies. Inspect with `docker image ls` or registry tooling. Smaller images usually transfer faster, but image size does not dictate RAM consumption.
2. **Runtime RAM:** The app's live heap, stacks, native allocations, and buffers. It changes with traffic. A Dockerfile has no CPU/memory reservation or hard-limit instruction. A local Docker engine can apply `docker run --memory` and `--cpus` at runtime.
3. **Kubernetes CPU/memory:** `resources.requests` influence scheduling and CPU shares; `resources.limits` impose ceilings. CPU beyond a limit is throttled; memory beyond a limit can cause `OOMKilled`. For example, `250m` means one quarter of a CPU core, while `512Mi` is 512 mebibytes of RAM.
4. **Writable disk:** Container logs, temporary files, and writable layers consume node ephemeral storage. Kubernetes can set `ephemeral-storage` requests and limits. Image layers consume node disk too, but a Pod's writable-layer limit is not an image-size cap.

Illustrative Kubernetes container settings (not yet measured or deployed):

```yaml
resources:
  requests:
    cpu: 250m
    memory: 256Mi
  limits:
    cpu: 500m
    memory: 512Mi
```

The scheduler uses the `250m` and `256Mi` requests to decide whether the Pod fits a node. A CPU request also influences the container's share under contention. The container can use more when the node has room, until the CPU or memory limit is reached. These are starting hypotheses, not values to copy into production without measuring the workload.

The Java `-XX:MaxRAMPercentage=70.0` setting influences the maximum Java heap relative to detected available RAM. It is **not** a total container memory limit: metaspace, thread stacks, direct buffers, and the JVM itself need headroom. We will choose initial Kubernetes requests and limits after an observed run, then adjust from metrics and failures.

## Verification without local Docker Desktop

The current `.github/workflows/app-ci.yml` has an `images` job on a GitHub-hosted `ubuntu-24.04` runner. After the PR opens, it runs `docker build -t orders-api:ci apps/orders-api` and `docker build -t payment-simulator:ci apps/payment-simulator`. The Java and Node test jobs must pass first because `images.needs` references them. Read the `images` job log for each build result. No local Docker daemon is needed.

The images are temporary on the runner: `docker build` alone does not publish them to ECR or prove they start. ECR publishing and a real EKS runtime smoke test are separate checkpoints. This distinction matters in interviews: build success, registry push, Kubernetes scheduling, readiness, and end-to-end HTTP behavior are different evidence.

## Troubleshooting

| Symptom | Likely cause | First check |
| --- | --- | --- |
| CI build cannot reach Docker daemon | Runner/engine setup issue | Inspect the `images` job runner and Docker step logs |
| `COPY ... not found` | Wrong build context or file excluded | Check final `docker build` path and `.dockerignore` |
| `npm ci` fails | `package-lock.json` mismatches `package.json` | Refresh lockfile with npm locally, then review diff |
| JAR not found in final stage | Artifact name differs from Dockerfile | Compare `pom.xml` version and `target/` output |
| EKS container exits immediately | Startup or configuration failure | `kubectl describe pod` and `kubectl logs --previous` |
| HTTP connection refused | App crashed, wrong port, or Service/endpoints issue | Check pod logs, readiness, Service selector, and endpoints |
| `EACCES`/permission denied | Non-root user cannot write to a path | Inspect file ownership and writable paths |
| `exec format error` on EKS | Image CPU architecture differs from node | Inspect image platform; build/publish for target architecture |
| `OOMKilled` | Memory usage exceeded container limit | Check `kubectl describe pod`, usage metrics, heap/native headroom |
| `Pending` with insufficient memory | Requests cannot fit on nodes | Check pod Events and node allocatable resources |

## Interview questions

1. **Image vs container?** An image is the built template; a container is an instance running from it.
2. **Why multi-stage for Java?** Compile and test with Maven, then ship only the JRE and runnable JAR.
3. **What does `.dockerignore` do?** Removes matching files from the build context, reducing transfer and accidental inclusion.
4. **`RUN` vs `CMD` vs `ENTRYPOINT`?** `RUN` is build-time; `CMD` is a replaceable startup default; `ENTRYPOINT` defines the main executable.
5. **Does `EXPOSE 8080` publish the app?** No. Use a container runtime port mapping locally or a Kubernetes Service later.
6. **Why run as non-root?** It limits what a compromised process can modify; ensure required paths remain readable/writable.
7. **What causes an image rebuild to be slow?** Cache invalidation after changed instructions or copied files; inspect layer ordering and dependencies.
8. **Can a Dockerfile reserve 512Mi at runtime?** No; set runtime flags or Kubernetes `resources`. Image disk size and runtime RAM are different.
9. **What do requests and limits do?** Requests guide scheduling; limits cap CPU and memory behavior. CPU is throttled; excess memory may lead to OOM kill.
10. **Why use multi-stage Node?** To copy only selected build results into the runtime stage; the gain depends on the app's build steps and base images. In this lab, it excludes the npm install cache but the Node base still contains npm.

References: [Dockerfile reference](https://docs.docker.com/reference/dockerfile), [multi-stage builds](https://docs.docker.com/get-started/docker-concepts/building-images/multi-stage-builds/), [build context](https://docs.docker.com/build/concepts/context/), [cache invalidation](https://docs.docker.com/build/cache/invalidation/), [Docker runtime constraints](https://docs.docker.com/engine/containers/resource_constraints/), [Kubernetes resources](https://kubernetes.io/docs/concepts/configuration/manage-resources-containers/), [Kubernetes ephemeral storage](https://kubernetes.io/docs/concepts/storage/ephemeral-storage/).
