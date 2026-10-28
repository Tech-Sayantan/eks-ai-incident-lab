# 06 — First AWS-backed network plan and Git basics

## Verified result (29 October 2026 IST)

[PR #3](https://github.com/Tech-Sayantan/eks-ai-incident-lab/pull/3) added the manual network-plan workflow and updated the PR path filter. Its static `check` job passed; GitHub recorded no review approval, and `Tech-Sayantan` squash-merged it as `a81275f`. The manual [workflow run 40761925321](https://github.com/Tech-Sayantan/eks-ai-incident-lab/actions/runs/40761925321) ran from that exact `main` commit. Every step passed. STS reported account `923988301700` and assumed role `eks-ai-incident-lab-gha-plan`; Terraform initialized the S3 backend and reported **Plan: 8 to add, 0 to change, 0 to destroy**.

Read-only AWS checks found no lab-tagged VPC, no lab Terraform state object, and no lab EKS cluster. This is verified cloud-planning evidence, not deployment evidence. Terraform's S3 backend can briefly create a lock object while planning; it does not create the VPC without `apply`.

## What the workflow proves

The workflow is manually dispatched from `main`. GitHub's OIDC token is accepted by AWS STS, which gives temporary credentials for the scoped plan role. The role reads the exact lab backend and AWS network metadata. Terraform compares the desired network in Git with the current remote state and reports eight proposed resources. A green PR static check, a successful cloud plan, and an applied network are three different evidence levels.

## Git staging: the quick inspection set

```bash
git status
git diff --cached --name-only
git diff --cached
git diff
```

`git add` copies the current file contents into Git's staging area (index). `git status` shows which files are staged. `git diff --cached --name-only` lists the staged paths; `git diff --cached` shows their staged contents. Plain `git diff` shows working-file edits that are still unstaged. A later edit to an already staged file is unstaged until added again. `git restore --staged <path>` removes a path from staging without deleting the working-file edit.

## Merge conflict versus cherry-pick

A merge conflict occurs when Git cannot choose how to combine competing edits, commonly two branches changing the same lines. Git stops and marks the disputed text. The developer reads both versions, writes the intended final content, stages the resolved file, and continues the merge. `git merge --abort` cancels an unfinished merge. A conflict is a request for a human decision, not proof either branch is wrong.

`git cherry-pick <commit>` copies the **change introduced by one existing commit** onto the current branch and usually creates a new commit SHA. It is useful for carrying one urgent fix from a feature branch to a release branch without merging the whole branch. It can also conflict; resolve and use `git cherry-pick --continue`, or use `git cherry-pick --abort` to cancel.

## Next session

Design the separate, more privileged infrastructure apply role and a manual apply workflow. Review the exact account, region, planned actions, and short-lived lab window before applying the network. After apply, verify the VPC, two subnets, route table, internet gateway, and Terraform state through AWS and Terraform. EKS creation remains a later cost-gated checkpoint.

Sources: [Git diff](https://git-scm.com/docs/git-diff), [Git merge](https://git-scm.com/docs/git-merge), [Git cherry-pick](https://git-scm.com/docs/git-cherry-pick), [Terraform plan](https://developer.hashicorp.com/terraform/cli/commands/plan).
