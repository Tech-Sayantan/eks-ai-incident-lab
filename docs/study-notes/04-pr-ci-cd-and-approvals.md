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

### Current EKS PR and Terraform delivery pattern

[EKS PR #9](https://github.com/Tech-Sayantan/eks-ai-incident-lab/pull/9) was opened once, on 31 October 2026 at 18:08:51 IST, after the EKS code commit was pushed. Later `git push` commands updated that same PR and reran its checks; they did not create new PRs. Its `check` job runs Terraform formatting/validation and Trivy, without an AWS plan or apply. The new `lab-plan.yml` and `lab-apply.yml` are manual workflows restricted to `main`; they become runnable after merge. A successful PR check is neither a human review nor a cloud deployment.

In real teams, **plan and apply are separate decisions**, but they need not be separate YAML files. One pipeline can have a plan job, approval gate, and apply job; another can plan on a PR and run a guarded apply after merge. Our separate manual plan is a preview. The apply workflow makes a **fresh plan**, checks its 13-create EKS guard, and applies that same saved plan. We do not assume an older preview is still accurate if cloud state or inputs changed. A saved plan contains configuration and input values, so never commit it or expose it as a public artifact. [Terraform planning modes](https://developer.hashicorp.com/terraform/cli/commands/plan), [applying saved plans](https://developer.hashicorp.com/terraform/cli/commands/apply), [GitHub environment approvals](https://docs.github.com/en/actions/reference/workflows-and-actions/deployments-and-environments).

1. **PR opened or updated:** a `pull_request` workflow runs if its event and path filters match. Reviewers can see the code diff, comments and check results. A review can be submitted before checks finish; a later code change may require another review if the repository enforces stale-review dismissal.
2. **Approval:** a reviewer submitting `Approve` expresses that the code is ready. Approval does not itself merge. Checks and reviews are independent signals. With suitable branch protection, GitHub can require both before merge. Without that protection, maintainers must enforce the policy manually.
3. **Merge:** combines the accepted branch into `main`. It changes Git history. It triggers CD only if a workflow or GitOps controller watches the resulting Git event or desired-state change.
4. **Deployment:** a separate job may build/publish an artifact, update environment configuration, or run a reviewed Terraform plan. A manual `workflow_dispatch` is another possible trigger. Verify the deployed result; a green build is not proof of a healthy environment.

The repository was private on GitHub Free through PR #2, when required branch protection and required environment reviewers were unavailable for that combination. Tan made it public on 29 October 2026. Public visibility did not automatically install branch protection. On 31 October, GitHub's branch-protection API reports that `main` requires the `check` job and requires zero human review approvals. Neither PR #1 nor PR #2 had a formal approving review. The connected `Tech-Sayantan` account merged both; a merge is not a review approval.

## PR #2: what squash actually did

[PR #2](https://github.com/Tech-Sayantan/eks-ai-incident-lab/pull/2) contained two feature-branch commits: `35c303e` added this checkpoint's study notes, and `c998cab` added the OIDC Terraform role. The Terraform `check` job passed in [run 40758594823](https://github.com/Tech-Sayantan/eks-ai-incident-lab/actions/runs/40758594823). GitHub records **zero reviews** and a merge by `Tech-Sayantan`. `--squash` combined the two commits' final file changes into one new `main` commit, `3f481c7`. The original two commits remain visible in the PR; `main` has the one combined commit. `--delete-branch` removed the remote feature branch after merging. No GitHub actor approved the PR; the merge decision was made without an enforced approval rule.

```text
feature:  35c303e (notes) -> c998cab (Terraform)
                                  | squash merge
main:     d5457cf -----------> 3f481c7 (both changes)
```

## This lab's infrastructure delivery

```text
Terraform branch -> PR -> fmt/validate/Trivy (implemented)
                  -> review -> merge to main
                  -> manual cloud plan from main via scoped OIDC role (PR #9)
                  -> separate manual apply run with fresh saved plan
                  -> apply exactly that saved plan -> verify AWS and state
```

Security refinement on 29 October 2026: Terraform state may contain future database secrets. A PR workflow that checks out proposed code is a weaker trust boundary, so this compact solo lab keeps PR jobs static and runs the AWS-backed plan only from `main`. The planning role needs read access to the relevant AWS resources and narrowly scoped S3 state/lock access; S3 backend operations may also need write access to the exact state object and lock file. The apply role is separate and more privileged; PR #9 proposes its EKS policy, which is not yet applied in AWS. The identity-only GitHub OIDC smoke-test role cannot plan or apply. The guarded apply plan must be generated from the exact trusted revision, account, Region and inputs it applies.

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
- **Why plan after merge?** A PR check verifies code and configuration without cloud credentials. Plan the trusted `main` revision against live state, review it, and apply only that reviewed revision.
- **CI says success but app is down:** build/test success proves the artifact checks, not runtime health. Inspect rollout, Pods, probes, Service/Ingress, logs and smoke-test results.
- **PR check never starts:** check the workflow's trigger, changed-path filters, branch, repository Actions settings and run registration delay.
- **Local Terraform appears frozen even though AWS CLI works:** on 29 October 2026, `terraform state list` and `plan` stalled after successful AWS STS authentication. The cached AWS provider executable under ignored `.terraform/providers` had its full logical size but zero allocated data blocks. A fresh download in a disposable backend probe read the eight bootstrap resources; replacing only the generated provider cache restored the real directory. The subsequent bootstrap plan showed **No changes**. Diagnose the stage of the stall before blaming IAM or force-unlocking state; never delete remote state to fix a local provider cache problem.

Sources: [GitHub workflow triggers](https://docs.github.com/en/actions/how-tos/write-workflows/choose-when-workflows-run/trigger-a-workflow), [PR review](https://docs.github.com/en/pull-requests/how-tos/review-pull-requests/approving-a-pull-request-with-required-reviews), [branch protection availability](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/managing-a-branch-protection-rule), [deployment environments](https://docs.github.com/en/actions/how-tos/deploy/configure-and-manage-deployments/manage-environments), [Argo CD automatic sync](https://argo-cd.readthedocs.io/en/stable/user-guide/auto_sync/).
