# GitOps & ArgoCD: Senior / Lead DevOps Interview Scenarios (6+ Years Experience)

---

### Scenario 1: The OutOfSync Infinite Loop & Mutating Webhook Conflict
**Context**: An ArgoCD application deployment is stuck in an infinite reconciliation loop. The status flashes between `Synced` and `OutOfSync` every 3 seconds. The ArgoCD application controller CPU spikes to 100%.

**Interview Question**:
> *"What causes this infinite OutOfSync oscillation, how do you diagnose it, and what is the resolution?"*

**Expected Senior/Lead Response**:
1. **Root Cause Identification**:
   - This occurs when an in-cluster dynamic controller or **Mutating Admission Webhook** (e.g., Istio Sidecar Injector, Linkerd, Datadog Admission Controller, or HPA modifying `replicas`) alters the live resource manifest after it is applied.
   - For example:
     - Git declares `replicas: 3`.
     - Horizontal Pod Autoscaler (HPA) scales the live pods to 8.
     - ArgoCD sees live `replicas: 8` != desired `replicas: 3`, marks it `OutOfSync`, and resets live pods to 3.
     - HPA immediately scales back to 8 $\rightarrow$ Infinite destructive loop!
2. **Resolution Strategies**:
   - **Strategy 1: `ignoreDifferences` in ArgoCD Application**:
     Instruct ArgoCD's diffing engine to ignore fields managed by in-cluster controllers:
     ```yaml
     spec:
       ignoreDifferences:
         - group: apps
           kind: Deployment
           jsonPointers:
             - /spec/replicas
         - group: ""
           kind: ServiceAccount
           jsonPointers:
             - /secrets  # Auto-injected tokens in older K8s versions
     ```
   - **Strategy 2: Remove mutating fields from Git**: Omit `spec.replicas` entirely from the Deployment manifest if an HPA is attached.

---

### Scenario 2: Database Schema Migrations with Sync Waves & Safe Rollback
**Context**: A microservice release includes a breaking PostgreSQL database schema change (adding non-nullable columns) and a new application container image.

**Interview Question**:
> *"How do you guarantee that the database migration executes and completes successfully before the new application pods start, and what happens if the migration fails?"*

**Expected Senior/Lead Response**:
1. **Sync Wave & Hook Architecture**:
   - Wrap the database migration in a Kubernetes `Job` resource annotated with:
     ```yaml
     annotations:
       argocd.argoproj.io/hook: PreSync
       argocd.argoproj.io/hook-delete-policy: BeforeHookCreation
       argocd.argoproj.io/sync-wave: "1"
     ```
   - Annotate the Deployment with `argocd.argoproj.io/sync-wave: "2"`.
2. **Execution Flow & Failure Handling**:
   - During Sync, ArgoCD detects Wave 1 (`PreSync` Hook) and triggers the migration Job.
   - ArgoCD pauses and monitors the Job until its status is `Complete`.
   - **If the Migration Fails**: The Job exits with non-zero status. ArgoCD immediately aborts the synchronization. Wave 2 (Application Deployment) **never starts**, ensuring existing production traffic continues running on the old, stable application version.
3. **Backward Compatibility Rule**:
   - Senior Rule: *All schema changes must be backward-compatible with the currently running application version.* (Expand and Contract pattern). Never drop columns or add non-default constraints in a single release.

---

### Scenario 3: Accidental Disaster: Preventing Mass Deletion via `prune: true`
**Context**: A junior developer makes a mistake in a Kustomize base overlay and deletes the path in Git. ArgoCD has `syncPolicy: automated: prune: true` enabled. Within seconds, ArgoCD could delete 50 production deployments.

**Interview Question**:
> *"What safety guards and architectural controls do you place on ArgoCD to prevent automated catastrophic resource deletion?"*

**Expected Senior/Lead Response**:
1. **Resource Protection Annotation**:
   - Annotate critical persistent resources (Databases, PVCs, StatefulSets, Namespaces) with:
     ```yaml
     metadata:
       annotations:
         argocd.argoproj.io/sync-options: Prune=false
     ```
     ArgoCD will never delete annotated resources, even if removed from Git.
2. **ArgoCD Self-Healing Safety Limits**:
   - Configure global controller flags: `--kube-api-qps` and rate-limiting safeguards.
   - Use **ArgoCD Project-level `destinations` and `orphanedResources` monitoring**: Warn and alert before automatic deletion.
3. **Git Branch Protection & CODEOWNERS**:
   - Strict branch protection on the GitOps configuration repo: Requires 2 Senior Platform engineer approvals on changes touching production overlays.

---

### Scenario 4: Automated Image Updates vs. Git Merge Conflicts at Scale
**Context**: You have 150 developers pushing code. Every CI build automatically updates image tags in the GitOps repository via ArgoCD Image Updater or CI git commit scripts. Frequent concurrent commits cause Git push rejections (`fetch first`, merge conflicts).

**Interview Question**:
> *"How do you design a high-frequency automated GitOps release pipeline that avoids merge conflicts and race conditions?"*

**Expected Senior/Lead Response**:
1. **De-couple Environments by Branch or Directory**:
   - Structure the GitOps repo by directories (`services/service-a/env/prod/image.yaml`), not one giant monolithic file.
2. **Kustomize Image Edit Strategy**:
   - Use `kustomize edit set image` isolated to the specific service's directory.
3. **Pull-Request Based Promotion Loop**:
   - Rather than committing directly to `main`, the CI pipeline opens an automated PR (or updates an automated staging branch).
   - Use an automated merge queue (GitHub Merge Queue) with branch concurrency controls:
     ```yaml
     concurrency:
       group: gitops-deploy-${{ matrix.service }}
       max-running: 1
     ```
4. **Parameter Overrides via ArgoCD CLI / Application API (Zero Git Commit Hot-Patch)**:
   - For ephemeral preview environments, pass temporary image tags dynamically via ArgoCD parameter overrides without polluting Git commit logs.

---

### Scenario 5: Disaster Recovery: 15-Minute Cluster Re-hydration
**Context**: An entire AWS region hosting your primary production EKS cluster experiences a catastrophic outage. You must spin up an identical cluster in another region (`eu-central-1`) and restore all 200 services.

**Interview Question**:
> *"Walk me through the GitOps disaster recovery process from empty AWS VPC to 100% restored production traffic."*

**Expected Senior/Lead Response**:
1. **Infrastructure Re-hydration via Terraform / OpenTofu**:
   - Run Terraform pipeline to provision VPC, Subnets, and EKS cluster in the secondary region (~8-10 minutes).
2. **Bootstrap ArgoCD via Helm**:
   - Install ArgoCD controller and bootstrap the **App-of-Apps** or root **ApplicationSet** pointing to the GitOps control repository.
3. **Automated Application Reconciliation**:
   - ArgoCD starts up, connects to Git, detects the newly registered cluster target, and pulls:
     - Wave -1: Cert-Manager, Ingress Controllers, Service Mesh.
     - Wave 0: External Secrets Operator & SecretStores (authenticating to regional Vault).
     - Wave 1-3: 200 application deployments, services, HPAs.
4. **DNS Failover via Route53 / Cloudflare**:
   - Health checks on primary region fail; automated latency/failover routing points traffic to the newly synced secondary cluster ingress. Zero manual `kubectl apply` commands executed.
