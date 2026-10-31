# Jenkins Enterprise: Senior / Lead DevOps Interview Scenarios (6+ Years Experience)

---

### Scenario 1: Jenkins Controller JVM OOMKilled & Massive GC Latency Spikes
**Context**: An enterprise Jenkins controller managing 600 pipelines and 3,000 jobs crashes every Monday morning. Kubernetes terminates the master pod with `Exit Code 137 (OOMKilled)`. Thread dumps show 15-second Stop-The-World GC pauses.

**Interview Question**:
> *"How do you diagnose, remediate, and architecturally harden a Jenkins controller suffering from fatal memory exhaustion?"*

**Expected Senior/Lead Response**:
1. **Root Cause Analysis (Memory & Thread Profiling)**:
   - Capture JVM heap dump before crash (`-XX:+HeapDumpOnOutOfMemoryError -XX:HeapDumpPath=/var/jenkins_home/heapdumps/`).
   - Analyze heap dump with Eclipse Memory Analyzer (MAT). Common culprits:
     - **Multibranch Pipeline Indexing**: Scanning hundreds of GitHub repos simultaneously loading thousands of Git trees into heap.
     - **Groovy CPS script execution leak**: Unbounded pipeline build histories keeping references in memory.
2. **Remediation & JVM Architecture**:
   - Transition to **G1GC** (`-XX:+UseG1GC -XX:InitiatingHeapOccupancyPercent=45 -XX:G1ReservePercent=15`).
   - Move build execution completely off the master: Set controller `numExecutors: 0`. The controller must act *purely* as an event coordinator, never compiling code.
   - Throttle Git branch indexing using webhook-driven scanning (`github-webhook/`) instead of aggressive periodic polling.
3. **Storage & Inode Management**:
   - Enforce global `buildDiscarder(logRotator(numToKeepStr: '30', daysToKeepStr: '14'))` via JCasC.
   - Mount `JENKINS_HOME` on high-performance AWS `gp3` storage with IOPS throttles detached from capacity.

---

### Scenario 2: The `NotSerializableException` in Groovy CPS Pipelines
**Context**: A developer writes a shared library step that instantiates a custom non-serializable Java class or an HTTP client object. Halfway through the pipeline, Jenkins throws `java.io.NotSerializableException`.

**Interview Question**:
> *"Why does Jenkins require CPS serialization, what causes this exception, and how do you resolve it?"*

**Expected Senior/Lead Response**:
1. **Underlying Architecture (Continuation-Passing Style - CPS)**:
   - Jenkins pipelines are designed to survive controller restarts mid-execution. To achieve this, Jenkins pauses the Groovy execution state at every step and serializes the call stack and local variables to disk.
   - Any variable held in memory across a pipeline step (like `sh`, `echo`, or `input`) must implement `java.io.Serializable`.
2. **Resolution Patterns**:
   - **Pattern A (Scope Closure)**: Nullify or scope non-serializable objects within standalone blocks that do not span Jenkins pipeline steps:
     ```groovy
     // BAD: holds non-serializable object across a step
     def matcher = (text =~ /regex/)
     sh "echo 'doing something'" // CRASH: matcher is in scope across step!
     
     // GOOD: isolate non-serializable object
     @NonCPS
     def extractMatch(text) {
         def matcher = (text =~ /regex/)
         return matcher ? matcher[0][1] : null
     }
     ```
   - **Pattern B (`@NonCPS` annotation)**: Annotate helper methods that perform complex loops, regex matching, or object creation with `@NonCPS`. This instructs Jenkins to execute the code using standard Groovy without serializing state.

---

### Scenario 3: Container Escape via Docker Socket (`docker.sock`)
**Context**: A security audit flags that your Jenkins agents mount `/var/run/docker.sock` from the Kubernetes worker nodes to run `docker build`. The auditor flags this as a Critical CIS Benchmark violation.

**Interview Question**:
> *"Explain why mounting `docker.sock` is a critical vulnerability, and what is your architectural migration path to daemonless container builds?"*

**Expected Senior/Lead Response**:
1. **Security Vulnerability (Privilege Escalation)**:
   - Mounting `/var/run/docker.sock` grants root-level control over the host node's Docker daemon.
   - Any malicious developer or compromised third-party dependency can run:
     `docker run -v /:/host -it alpine chroot /host`
     This achieves full root host takeover, compromising every pod and secret residing on that Kubernetes node.
2. **Architectural Replacement Solutions**:
   - **Kaniko (Google Container Tools)**: Executes inside user-space without any Docker daemon or root privileges. Snapshots the filesystem in memory and pushes directly to OCI registries.
   - **BuildKit / Rootless Buildx**: Runs unprivileged BuildKit daemon inside the pod using user namespaces.
   - **AWS Pod Identity / IRSA**: Combine Kaniko with AWS IAM Roles for Service Accounts (IRSA) so that temporary STS tokens are used to push to ECR, leaving zero static credentials on disk.

---

### Scenario 4: Strategic Migration from Jenkins to GitHub Actions
**Context**: Leadership wants to decommission a 7-year-old Jenkins cluster costing \$15,000/month in EC2 instances and maintenance, migrating 400 microservices to GitHub Actions.

**Interview Question**:
> *"What is your 5-phase enterprise migration strategy to move 400 microservices from Jenkins to GitHub Actions with zero downtime?"*

**Expected Senior/Lead Response**:
1. **Phase 1: Foundation & Infrastructure**:
   - Deploy Actions Runner Controller (ARC) on existing EKS clusters to leverage internal VPC networks and avoid cloud runner egress costs.
   - Configure AWS OIDC federation to eliminate static AWS keys.
2. **Phase 2: Golden Reusable Workflows**:
   - Convert Jenkins Shared Libraries (`vars/*.groovy`) into centrally governed GitHub Actions **Reusable Workflows** (`.github/workflows/reusable-ci.yml`).
   - Validate that SonarQube, Trivy, and image signing gates match or exceed existing security baselines.
3. **Phase 3: Dual-Running (Shadow Execution)**:
   - Run both Jenkins and GitHub Actions concurrently on a pilot cohort of 20 tier-2 microservices.
   - Compare build times, test coverage reports, and container digests to ensure parity. Jenkins remains the authoritative deployment trigger during this phase.
4. **Phase 4: Flipping Deployment Authority**:
   - Switch GitHub Actions to push the authoritative GitOps commit to ArgoCD.
   - Demote Jenkins jobs to read-only/disabled for those services.
5. **Phase 5: Decommission & Cost Auditing**:
   - Sunset Jenkins masters, delete legacy EBS volumes, archive build history to S3 Glacier for audit compliance, and decommission Jenkins server infrastructure.
