"""
==============================================================================
Production AI DevOps & SRE Incident Triage Agent
==============================================================================
This agent implements the ReAct (Reason + Act) loop using LLM Tool Calling.
It connects to a Kubernetes cluster, diagnoses failing pods (CrashLoopBackOff,
OOMKilled, ImagePullBackOff), fetches crash logs, and synthesizes root-cause
analysis with GitOps remediation recommendations.
==============================================================================
"""

import os
import json
from typing import Dict, Any, List

# Simulating standard Tool Calling function signatures (compatible with OpenAI, Gemini, Claude, LangChain)
class KubernetesTools:
    """Sandboxed Kubernetes Read-Only Diagnostics Tools"""

    @staticmethod
    def list_unhealthy_pods(namespace: str) -> List[Dict[str, Any]]:
        """Scans the namespace for pods not in Ready/Running state."""
        # In live production: client.CoreV1Api().list_namespaced_pod(namespace)
        # Mocking live cluster response for reference execution
        return [
            {
                "pod_name": "payment-processor-7c89f489b5-x2n8k",
                "namespace": namespace,
                "status": "CrashLoopBackOff",
                "restart_count": 8,
                "container_name": "payment-api",
                "last_termination_reason": "OOMKilled",
                "exit_code": 137,
                "node": "ip-10-0-42-18.ec2.internal"
            }
        ]

    @staticmethod
    def get_pod_events(namespace: str, pod_name: str) -> List[str]:
        """Retrieves recent Kubernetes events associated with the pod."""
        return [
            "Normal Scheduled 12m default-scheduler Successfully assigned payment-prod/payment-processor-7c89f489b5-x2n8k",
            "Warning BackOff 3m kubelet Back-off restarting failed container payment-api in pod payment-processor-7c89f489b5-x2n8k",
            "Warning OOMKilled 2m kernel Task in /kubepods.slice killed as a result of limit exhaustion"
        ]

    @staticmethod
    def get_container_logs(namespace: str, pod_name: str, previous: bool = True) -> str:
        """Retrieves standard out / standard error logs from the terminated container."""
        return (
            "[2026-11-02 12:04:11] INFO: Initializing Payment Gateway Service v3.2.0\n"
            "[2026-11-02 12:04:12] INFO: Connecting to PostgreSQL Aurora Cluster...\n"
            "[2026-11-02 12:04:14] WARN: Processing high-volume batch transaction payload (50,000 records)\n"
            "[2026-11-02 12:04:15] java.lang.OutOfMemoryError: Java heap space\n"
            "\tat java.base/java.util.Arrays.copyOf(Arrays.java:3537)\n"
            "\tat com.enterprise.payment.BatchProcessor.process(BatchProcessor.java:184)\n"
            "Killed\n"
        )

    @staticmethod
    def check_gitops_recent_diff(app_name: str) -> Dict[str, Any]:
        """Queries GitOps / ArgoCD repo for the most recent deployment change."""
        return {
            "app_name": app_name,
            "recent_commit": "a8f1bc4",
            "author": "developer@company.com",
            "message": "perf: adjust payment pod resources for cost savings",
            "diff": "- memory: 4Gi\n+ memory: 1Gi"
        }


class SRETriageAgent:
    """The Autonomous SRE Agent Controller"""

    def __init__(self, target_namespace: str = "payment-prod"):
        self.namespace = target_namespace
        self.tools = KubernetesTools()
        self.memory: List[Dict[str, Any]] = []

    def log_thought(self, thought: str):
        print(f"\n🧠 [AGENT THOUGHT]: {thought}")

    def log_action(self, tool_name: str, args: Dict[str, Any]):
        print(f"⚡ [AGENT ACTION]: Invoking tool `{tool_name}` with args: {json.dumps(args)}")

    def run_investigation(self) -> Dict[str, Any]:
        print(f"🚀 Starting Autonomous SRE Investigation in namespace `{self.namespace}`...")

        # Step 1: Observe Unhealthy Pods
        self.log_thought("I need to check if any pods are crashing or in an unhealthy state.")
        self.log_action("list_unhealthy_pods", {"namespace": self.namespace})
        unhealthy_pods = self.tools.list_unhealthy_pods(self.namespace)

        if not unhealthy_pods:
            return {"status": "HEALTHY", "message": "All pods running normally."}

        target_pod = unhealthy_pods[0]
        pod_name = target_pod["pod_name"]
        print(f"⚠️ Detected Failing Pod: {pod_name} | Reason: {target_pod['last_termination_reason']} (Exit Code: {target_pod['exit_code']})")

        # Step 2: Fetch Kubernetes Events
        self.log_thought(f"Pod {pod_name} died with exit code 137. I will check the cluster events for OOM or Eviction signals.")
        self.log_action("get_pod_events", {"pod_name": pod_name, "namespace": self.namespace})
        events = self.tools.get_pod_events(self.namespace, pod_name)
        print(f"📋 Events fetched ({len(events)} events found)")

        # Step 3: Fetch Termination Logs
        self.log_thought("Exit code 137 confirms SIGKILL by kernel. Let me inspect the previous container logs for Java heap exhaustion or application panics.")
        self.log_action("get_container_logs", {"pod_name": pod_name, "previous": True})
        logs = self.tools.get_container_logs(self.namespace, pod_name, previous=True)
        print("📄 Logs extracted from crash buffer.")

        # Step 4: Cross-reference with GitOps repo
        self.log_thought("Logs show `java.lang.OutOfMemoryError: Java heap space`. Did a recent GitOps deployment reduce memory limits or introduce a memory leak?")
        self.log_action("check_gitops_recent_diff", {"app_name": "payment-processor"})
        git_diff = self.tools.check_gitops_recent_diff("payment-processor")

        # Step 5: Synthesize RCA & Actionable Remediation Plan
        self.log_thought("Root cause proven: Commit a8f1bc4 slashed memory limits from 4Gi to 1Gi, starving the JVM heap during batch processing.")
        
        incident_report = {
            "incident_id": "INC-2026-K8S-091",
            "service": "payment-processor",
            "severity": "SEV-1 (Production degraded)",
            "root_cause": (
                "Pod terminated with Exit Code 137 (OOMKilled) triggered by JVM OutOfMemoryError. "
                "Recent GitOps commit a8f1bc4 reduced pod memory limits from 4Gi to 1Gi, "
                "which is insufficient for standard batch transaction workloads."
            ),
            "remediation_plan": [
                "1. Immediate Action: Revert GitOps commit a8f1bc4 to restore 4Gi memory limit.",
                "2. Trigger ArgoCD sync to update deployment rollout.",
                "3. Configure JVM MaxRAMPercentage: -XX:MaxRAMPercentage=75.0 inside container environment."
            ],
            "gitops_revert_pr": "https://github.com/purnareddy9/devops-gitops-manifests/pull/482"
        }

        return incident_report


if __name__ == "__main__":
    agent = SRETriageAgent(target_namespace="payment-prod")
    report = agent.run_investigation()
    
    print("\n" + "="*70)
    print("📊 INCIDENT TRIAGE REPORT GENERATED BY DEVOPS AI AGENT")
    print("="*70)
    print(json.dumps(report, indent=2))
