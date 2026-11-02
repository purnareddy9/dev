# Module 05: Building Enterprise DevOps Agents

> **Focus Level**: Senior / Staff / Lead Platform & DevOps Engineer (6+ Years Experience)  
> **Key Domains**: CI/CD Runner Infrastructure (ARC & Dynamic Pods), Custom Hardened Agent Images, AI-Powered SRE & Triage Agents, Model Context Protocol (MCP) & Autonomous Self-Healing.

---

## ⚡ Animated Agent Architecture & Execution Loop

<p align="center">
  <img src="../assets/agent-architecture-animation.svg" alt="DevOps Agent Architecture Animation" width="100%" />
</p>

---

## The Dual Nature of "Agents" in Modern DevOps

When engineering leaders talk about "building agents for DevOps", they are operating across two critical pillars:

```mermaid
flowchart TD
    Agent[DevOps Agent Ecosystem]
    
    subgraph Pillar1["Pillar 1: CI/CD Execution Runners (Platform Compute)"]
        ARC[GitHub Actions Runner Controller - ARC]
        JNK_Agents[Jenkins Dynamic Kubernetes Pod Agents]
        Custom_Img[Hardened Container Images with Toolchains]
        Ephemeral[Ephemeral & Scale-to-Zero Compute via Karpenter]
    end

    subgraph Pillar2["Pillar 2: AI Autonomous DevOps Agents (Cognitive Automation)"]
        ReAct[ReAct Reasoning Loop: Observe -> Orient -> Decide -> Act]
        Tools[Tool Calling: Kubectl, Prometheus, ArgoCD, Git API]
        SRE_Agent[Automated Incident Triage: CrashLoopBackOff & 5xx]
        PR_Agent[Automated Pipeline Healer & GitOps Revert Agent]
    end

    Agent --> Pillar1
    Agent --> Pillar2
```

---

## Pillar 1: Building Custom CI/CD Execution Runners

Public cloud runners (GitHub-hosted or standard VM agents) suffer from:
1. **Security Vulnerabilities**: Mounting `/var/run/docker.sock` allows root container breakout.
2. **Egress & Ingress Bottlenecks**: Inability to talk to internal databases, Kafka brokers, or private artifact registries without opening public firewall rules.
3. **Slow Build Times**: Every runner spends 3-5 minutes downloading Java, Go, Python, Docker Buildx, Helm, Kubectl on every single pipeline run.

### The Solution: Custom Hardened Ephemeral Runner Containers
- Build an enterprise base image containing all necessary CLIs pre-installed and cached.
- Run as non-root user (`UID 1001:1001`).
- Deploy on Kubernetes using **Actions Runner Controller (ARC)** for GitHub Actions or **Kubernetes Cloud Plugin** for Jenkins.
- **Ephemeral Lifecycle**: Pod is provisioned on job dispatch $\rightarrow$ executes single job $\rightarrow$ destroyed immediately. Zero dirty state, zero toxic cache cross-contamination.

---

## Pillar 2: Building Autonomous AI DevOps & SRE Agents

An AI DevOps Agent is an autonomous program that connects an LLM (Large Language Model) to real-world infrastructure tools via **Function Calling / Tool Calling** or **Model Context Protocol (MCP)**.

### The ReAct (Reasoning + Acting) Agent Loop:

```mermaid
sequenceDiagram
    autonumber
    participant Alert as Prometheus / Datadog / PagerDuty
    participant Agent as DevOps AI Agent (LLM ReAct Loop)
    participant K8s as Kubernetes API
    participant GitOps as ArgoCD & GitHub API
    participant SRE as On-Call SRE (Slack)

    Alert->>Agent: Alert: Payment Service 5xx Spike (CrashLoopBackOff)
    Note over Agent: Reason: I need to inspect pod status and recent events.
    Agent->>K8s: Tool Call: get_pod_events(namespace='payment-prod')
    K8s-->>Agent: Warning: Back-off restarting failed container (Exit Code 137 OOMKilled)
    
    Note over Agent: Reason: Pod was OOMKilled. Let me fetch recent logs and check recent Git commits.
    Agent->>K8s: Tool Call: get_pod_logs(tail_lines=50, previous=True)
    K8s-->>Agent: Log: java.lang.OutOfMemoryError: Java heap space
    
    Agent->>GitOps: Tool Call: get_recent_gitops_diff(app='payment-service')
    GitOps-->>Agent: Diff: Replicas changed, Memory limit reduced from 4Gi to 1Gi in commit a8f1bc
    
    Note over Agent: Reason: Blast radius identified. Recent commit reduced memory limit causing OOMKill.
    Agent->>GitOps: Tool Call: create_revert_pr(commit='a8f1bc', reason='Fixes OOMKill crash')
    GitOps-->>Agent: PR #142 Created: [Revert] memory reduction
    
    Agent->>SRE: Slack Alert: "Diagnosed OOMKill caused by commit a8f1bc. Created Revert PR #142. Awaiting approval to merge."
```

---

## 📂 Production Code in this Module

1. [`cicd-runner-agents/Dockerfile.hardened-runner`](./cicd-runner-agents/Dockerfile.hardened-runner): Hardened multi-tool rootless container runner for GitHub ARC & Jenkins.
2. [`cicd-runner-agents/arc-runner-scaleset.yaml`](./cicd-runner-agents/arc-runner-scaleset.yaml): Production Kubernetes `AutoScalingRunnerSet` CRD with Karpenter spot autoscaling.
3. [`cicd-runner-agents/jenkins-k8s-pod-agent.yaml`](./cicd-runner-agents/jenkins-k8s-pod-agent.yaml): Kubernetes multi-container dynamic pod agent definition for Jenkins.
4. [`ai-devops-agents/architecture.md`](./ai-devops-agents/architecture.md): Architectural design for SRE AI agents, security guardrails, read-only vs write boundaries, and MCP integration.
5. [`ai-devops-agents/k8s_incident_triage_agent.py`](./ai-devops-agents/k8s_incident_triage_agent.py): Full working Python AI Agent implementing the ReAct pattern with live Kubernetes API tool-calling for automated root-cause analysis.
6. [`interview-scenarios.md`](./interview-scenarios.md): High-bar Senior / Principal DevOps interview scenarios on runner fleet scaling and AI agent safety.
