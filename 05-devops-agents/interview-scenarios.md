# DevOps Agents: Senior / Lead Interview Scenarios (6+ Years Experience)

---

### Scenario 1: Mitigating Runner Security Risks: DinD vs. Rootless Kaniko vs. Socket Mounting
**Context**: A security architect objects to using standard Docker-in-Docker (`privileged: true`) or mounting `/var/run/docker.sock` in your self-hosted Kubernetes runner fleet.

**Interview Question**:
> *"Compare the security architectures of Docker socket mounting, Docker-in-Docker (DinD), and Daemonless Kaniko. How do you design an enterprise-grade secure CI runner platform?"*

**Expected Senior/Lead Response**:
1. **The Vulnerability Hierarchy**:
   - **Mounted `/var/run/docker.sock` (Worst)**: Complete host takeover vulnerability. Any container running `docker run -v /:/host ...` escapes container boundaries and gains root on the underlying Kubernetes node.
   - **Privileged Docker-in-Docker (Moderate Risk)**: Container runs with `--privileged`, giving access to host devices and kernel capabilities. While scoped to the container's PID/mount namespace, a kernel zero-day allows host breakout.
   - **Daemonless Kaniko / Rootless BuildKit (Best Practice)**: Executes purely in unprivileged user space without root, without `--privileged`, and without access to any Docker socket.
2. **Enterprise Implementation**:
   - For standard application image builds: Enforce **Kaniko** or **Rootless BuildKit** in non-root runner pods (`UID 1001`).
   - If DinD is strictly mandatory (e.g. running Testcontainers during integration tests): Isolate runner pods onto dedicated, tainted Kubernetes node groups with strict AWS Security Groups and **Pod Security Standards: Baseline/Restricted**.

---

### Scenario 2: Runner Fleet Autoscaling: Slashing 20-Minute Queues to <45 Seconds
**Context**: During peak sprint deliveries, 30 teams push code simultaneously. The GitHub runner queue spikes to 150 pending jobs. Standard Kubernetes Cluster Autoscaler takes 5-8 minutes to add EC2 nodes, causing frustrated developers.

**Interview Question**:
> *"How do you design a zero-to-scale CI runner architecture on AWS EKS that provisions compute in under 45 seconds while cutting EC2 costs by 70%?"*

**Expected Senior/Lead Response**:
1. **Replace Cluster Autoscaler with Karpenter**:
   - Karpenter bypasses AWS Auto Scaling Groups (ASGs). It talks directly to AWS EC2 fleet APIs to provision right-sized nodes in ~35-45 seconds in response to pending Pod signals.
2. **Diversified Spot Instance Provisioning**:
   - Configure Karpenter `NodePool` to leverage AWS Spot instances across 15+ instance types (`c5.xlarge`, `c6i.xlarge`, `m5.xlarge`, `m6i.xlarge`).
   - Enable **AWS Node Termination Handler** or Karpenter's native interruption queue to handle EC2 2-minute spot rebalance warnings gracefully.
3. **Webhook-Driven Autoscaling in ARC**:
   - Switch Actions Runner Controller (ARC) from polling mode to **Webhook-driven mode** via an internal Ingress controller. Runners start provisioning the millisecond a `workflow_job.queued` webhook arrives.
4. **Scale-to-Zero (`minRunners: 0`)**:
   - Outside business hours, all runner pods scale down to zero. Zero idle EC2 instances running overnight.

---

### Scenario 3: Guardrailing Autonomous AI SRE Agents in Production
**Context**: Your platform team is deploying an AI agent that listens to AlertManager and triages Kubernetes cluster incidents. Leadership worries the AI might execute a dangerous command or hallucinate a non-existent flag during an outage.

**Interview Question**:
> *"What architectural guardrails, RBAC policies, and blast-radius constraints do you enforce when giving an AI agent access to production infrastructure?"*

**Expected Senior/Lead Response**:
1. **Strict Read vs. Mutate Boundary (Dual-Plane Architecture)**:
   - **Diagnostic Plane (Autonomous / Read-Only)**: Agent is granted read-only Kubernetes RBAC (`get`, `list`, `watch` on Pods, Services, Events, Logs). It can independently query Prometheus and inspect logs without human approval.
   - **Action Plane (Human-in-the-Loop)**: Any mutating action (scaling deployments, restarting pods, editing manifests) **cannot be executed directly by the LLM**.
2. **GitOps as the Sole Enforcement Point**:
   - The agent never runs `kubectl delete` or `kubectl apply`.
   - Instead, the agent generates a **Git Revert PR** or an **ArgoCD rollback request** with a documented post-mortem explanation and posts an interactive card to Slack.
   - An on-call SRE clicks **"Approve & Merge"**. The GitOps engine (ArgoCD) reconciles the change.
3. **Deterministic Tool Schema Validation**:
   - Tools are validated using Pydantic schemas. If the model hallucinates an invalid argument or non-whitelisted namespace, the execution halts before touching the Kubernetes API.
4. **Audit Logging & Tracing**:
   - Every agent prompt, thought step, and tool invocation is logged into an OpenTelemetry tracing backend (e.g. Langfuse / Arize Phoenix) for full post-incident auditability.
