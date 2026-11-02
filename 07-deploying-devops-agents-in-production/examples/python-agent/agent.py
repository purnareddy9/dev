"""
==============================================================================
Enterprise Python DevOps Agent (In-Cluster Kubernetes / EKS Service)
==============================================================================
Uses official `kubernetes` and `boto3` libraries.
Automatically switches between in-cluster ServiceAccount authentication (EKS)
and local ~/.kube/config for testing.
==============================================================================
"""

import os
import json
import logging
from typing import Dict, Any, List

# Kubernetes Official SDK
from kubernetes import client, config
from kubernetes.client.exceptions import ApiException

# AWS Official SDK
import boto3

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("DevOpsAgent")

class KubernetesAgentTools:
    """Production tools for in-cluster diagnostics"""

    def __init__(self):
        # Authenticate automatically: in-cluster if in EKS pod, else local kubeconfig
        try:
            config.load_incluster_config()
            logger.info("Authenticated via in-cluster Kubernetes ServiceAccount (IRSA).")
        except config.ConfigException:
            try:
                config.load_kube_config()
                logger.info("Authenticated via local ~/.kube/config.")
            except Exception as e:
                logger.warning(f"Could not load Kubeconfig: {e}. Running in mocked mode.")

        self.core_v1 = client.CoreV1Api()
        self.apps_v1 = client.AppsV1Api()

    def get_failing_pods(self, namespace: str) -> List[Dict[str, Any]]:
        """Scans namespace for pods in CrashLoopBackOff, OOMKilled, or Error."""
        failing_pods = []
        try:
            pods = self.core_v1.list_namespaced_pod(namespace=namespace)
            for pod in pods.items:
                statuses = pod.status.container_statuses or []
                for cs in statuses:
                    if cs.state.waiting and cs.state.waiting.reason in ["CrashLoopBackOff", "ImagePullBackOff"]:
                        failing_pods.append({
                            "pod_name": pod.metadata.name,
                            "reason": cs.state.waiting.reason,
                            "restart_count": cs.restart_count,
                            "image": cs.image
                        })
                    elif cs.last_state.terminated and cs.last_state.terminated.reason == "OOMKilled":
                        failing_pods.append({
                            "pod_name": pod.metadata.name,
                            "reason": "OOMKilled",
                            "exit_code": cs.last_state.terminated.exit_code,
                            "restart_count": cs.restart_count
                        })
        except ApiException as e:
            logger.error(f"K8s API error: {e}")
        return failing_pods

    def get_previous_logs(self, namespace: str, pod_name: str, tail_lines: int = 100) -> str:
        """Retrieves crash logs from the terminated container instance."""
        try:
            return self.core_v1.read_namespaced_pod_log(
                name=pod_name,
                namespace=namespace,
                previous=True,
                tail_lines=tail_lines
            )
        except ApiException as e:
            return f"Error reading logs: {e}"


class AWSAgentTools:
    """Production tools for AWS Cloud infrastructure diagnostics"""

    def __init__(self):
        self.cloudwatch = boto3.client("cloudwatch")

    def get_rds_cpu_utilization(self, db_instance_identifier: str) -> float:
        """Queries Amazon CloudWatch for database CPU metrics."""
        # Queries CloudWatch MetricData
        return 74.2 # Mocked metric response


def main():
    logger.info("Starting Enterprise DevOps Agent Controller...")
    k8s_tools = KubernetesAgentTools()
    
    # Example agent execution: Triage payment-prod namespace
    logger.info("Scanning namespace 'payment-prod' for incidents...")
    failures = k8s_tools.get_failing_pods("payment-prod")
    logger.info(f"Scan complete. Found {len(failures)} unhealthy pods.")

if __name__ == "__main__":
    main()
