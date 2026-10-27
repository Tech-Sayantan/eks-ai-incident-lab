# 04 — PR, CI, CD and approvals

## What we actually verified

Network [PR #1](https://github.com/Tech-Sayantan/eks-ai-incident-lab/pull/1) proposed seven files. The initial CI run passed formatting and both Terraform validations, then failed Trivy rule `AWS-0164` for two public subnet instances. A documented inline exception was added only to that resource/rule; [the next run](https://github.com/Tech-Sayantan/eks-ai-incident-lab/actions/runs/40567235236) passed every step. GitHub recorded **zero review approvals**. On Tan's instruction, Trunks merged PR #1 using Tan's connected GitHub account; the merge commit is `291cc89`. Local `main` was fast-forwarded and clean. The current workflow has `pull_request` and manual `workflow_dispatch` triggers, and contains no `terraform apply` step. Direct AWS checks found no lab state object or lab-tagged VPC after merge.

## Git vocabulary

```text
working files --git add--> staging area --git commit--> local branch
local branch --git push--> GitHub branch --gh pr create--> pull request
```

- `git switch -c name`: create and enter a branch from the current commit.
- `git add path`: stage only the chosen files. Inspect with `git diff --cached` before committing.
- `git commit -m message`: save a local snapshot with a unique commit hash.
- `git push -u origin branch`: upload the branch and remember its upstream; later `git push` reuses that destination.
- `gh pr create --base main --head branch`: ask for a merge into `main`; opening a PR does not merge or deploy.
- `git pull --ff-only origin main`: move local `main` to the remote commit without inventing a local merge commit; it fails if local history has diverged.

## CI, review, merge, CD

1. **PR opened or updated:** a `pull_request` workflow runs if its event and path filters match. Reviewers can see the code diff, comments and check results. A review can be submitted before checks finish; a later code change may require another review if the repository enforces stale-review dismissal.
2. **Approval:** a reviewer submitting `Approve` expresses that the code is ready. Approval does not itself merge. Checks and reviews are independent signals. With suitable branch protection, GitHub can require both before merge. Without that protection, maintainers must enforce the policy manually.
3. **Merge:** combines the accepted branch into `main`. It changes Git history. It triggers CD only if a workflow or GitOps controller watches the resulting Git event or desired-state change.
4. **Deployment:** a separate job may build/publish an artifact, update environment configuration, or run a reviewed Terraform plan. A manual `workflow_dispatch` is another possible trigger. Verify the deployed result; a green build is not proof of a healthy environment.

This private repository uses GitHub Free. Required branch protection and required environment reviewers are unavailable for this combination. The lab therefore uses visible PR checks, a deliberate merge decision, and a separate manual apply trigger. There was no formal approving review on PR #1. The person who merged was the connected `Tech-Sayantan` account; a merge is not the same as a review approval.

## This lab's infrastructure delivery

```text
Terraform branch -> PR -> fmt/validate/Trivy (implemented)
                  -> cloud plan via scoped OIDC role (next)
                  -> review -> merge to main
                  -> manual dispatch -> fresh plan of main revision
                  -> apply exactly that plan -> verify AWS and state
```

The future PR planning role needs read access to the relevant AWS resources and narrowly scoped S3 state/lock access. The apply role will be separate and more privileged. The identity-only GitHub OIDC smoke-test role cannot plan or apply. Do not apply a saved PR plan after merge: its source revision or inputs may have changed. A job must bind the approved plan to the exact revision, account, Region and inputs it applies.

## Future Java application delivery

```text
Java PR -> Maven/Checkstyle/JUnit/JaCoCo -> Sonar quality gate
        -> Docker build + Trivy -> review and merge
main revision -> publish one scanned image to ECR -> record image digest
promotion -> update GitOps repo to that digest -> review/merge
Argo CD -> reconcile Kubernetes resources -> smoke test -> notify result
```

Building an image does not deploy it. Publishing to ECR makes it available; changing the GitOps repository's desired image digest makes a release eligible for deployment. With automated sync enabled, Argo CD detects desired-state changes and applies them to the cluster. A promotion approval belongs before the GitOps change reaches the tracked branch. After sync, health checks and a real request verify the outcome. This is the planned architecture; the Java app, ECR, GitOps and Argo CD steps have not yet been implemented.

## Interview questions and common failures

- **Does a green PR check mean approved?** No. It is an automated result, separate from a human review.
- **Does approval merge automatically?** No, unless a separately configured auto-merge process does so once all conditions are satisfied.
- **Does merging deploy?** Only if a `push` workflow, deployment trigger or GitOps reconciliation is configured. PR #1 did not deploy anything.
- **Why rerun a plan after merge?** The PR plan can be stale. Replan the exact trusted revision and apply the reviewed output.
- **CI says success but app is down:** build/test success proves the artifact checks, not runtime health. Inspect rollout, Pods, probes, Service/Ingress, logs and smoke-test results.
- **PR check never starts:** check the workflow's trigger, changed-path filters, branch, repository Actions settings and run registration delay.

Sources: [GitHub workflow triggers](https://docs.github.com/en/actions/how-tos/write-workflows/choose-when-workflows-run/trigger-a-workflow), [PR review](https://docs.github.com/en/pull-requests/how-tos/review-pull-requests/approving-a-pull-request-with-required-reviews), [branch protection availability](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/managing-a-branch-protection-rule), [deployment environments](https://docs.github.com/en/actions/how-tos/deploy/configure-and-manage-deployments/manage-environments), [Argo CD automatic sync](https://argo-cd.readthedocs.io/en/stable/user-guide/auto_sync/).
