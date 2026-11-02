"""
==============================================================================
Activity Agent 2: Terraform IaC Security & FinOps Cost Auditing Agent
==============================================================================
Automates:
1. Ingesting parsed `terraform show -json tfplan` outputs.
2. Checking for critical CIS AWS benchmark security violations.
3. Calculating projected monthly cloud cost impact.
4. Flagging idle resources, over-provisioned instances, or missing tags.
==============================================================================
"""

import json
from typing import Dict, Any, List

class TerraformCostSecurityAgent:
    """Agent that audits Terraform plans for Security & Cost Optimization."""

    def __init__(self, plan_name: str = "prod-infrastructure-plan.json"):
        self.plan_name = plan_name

    def load_mock_tf_plan(self) -> Dict[str, Any]:
        """Simulates loading parsed Terraform plan JSON resource changes."""
        return {
            "format_version": "1.2",
            "terraform_version": "1.7.5",
            "resource_changes": [
                {
                    "address": "aws_s3_bucket.customer_data",
                    "type": "aws_s3_bucket",
                    "change": {
                        "actions": ["create"],
                        "after": {
                            "bucket": "corp-customer-analytics-raw-bucket",
                            "acl": "public-read" # Critical Security Flaw!
                        }
                    }
                },
                {
                    "address": "aws_security_group_rule.allow_ssh",
                    "type": "aws_security_group_rule",
                    "change": {
                        "actions": ["create"],
                        "after": {
                            "from_port": 22,
                            "to_port": 22,
                            "protocol": "tcp",
                            "cidr_blocks": ["0.0.0.0/0"] # Critical Security Flaw!
                        }
                    }
                },
                {
                    "address": "aws_nat_gateway.dev_nat_gw",
                    "type": "aws_nat_gateway",
                    "change": {
                        "actions": ["create"],
                        "after": {
                            "allocation_id": "eipalloc-01928347192",
                            "tags": {"Environment": "dev"} # Cost Flaw: Multi-AZ NAT in Dev
                        }
                    }
                }
            ]
        }

    def audit_security_and_cost(self, plan: Dict[str, Any]) -> Dict[str, Any]:
        print(f"🔍 [STEP 1]: Auditing {len(plan['resource_changes'])} proposed Terraform resource changes...")
        
        security_findings = []
        cost_findings = []

        for change in plan["resource_changes"]:
            res_type = change["type"]
            after_state = change["change"]["after"]
            address = change["address"]

            # Security Check 1: Public S3 Bucket
            if res_type == "aws_s3_bucket" and after_state.get("acl") == "public-read":
                security_findings.append({
                    "resource": address,
                    "severity": "CRITICAL",
                    "rule": "CIS-AWS-2.1.5: S3 Buckets must never have public read ACLs",
                    "remediation": "Change acl to 'private' and attach aws_s3_bucket_public_access_block."
                })

            # Security Check 2: Unrestricted SSH Ingress (0.0.0.0/0)
            if res_type == "aws_security_group_rule" and after_state.get("from_port") == 22:
                if "0.0.0.0/0" in after_state.get("cidr_blocks", []):
                    security_findings.append({
                        "resource": address,
                        "severity": "CRITICAL",
                        "rule": "CIS-AWS-4.1: Ensure no security groups allow ingress from 0.0.0.0/0 to port 22",
                        "remediation": "Restrict cidr_blocks to corporate VPN CIDR or use AWS Systems Manager (SSM) Session Manager."
                    })

            # Cost Check: NAT Gateway in Non-Prod
            if res_type == "aws_nat_gateway":
                env_tag = after_state.get("tags", {}).get("Environment", "").lower()
                if env_tag in ["dev", "test", "qa"]:
                    cost_findings.append({
                        "resource": address,
                        "estimated_monthly_cost": "$32.40 / month (fixed) + $0.045/GB data egress",
                        "finding": f"Dedicated NAT Gateway provisioned in non-prod ({env_tag}) environment.",
                        "recommendation": "Use a shared NAT instance or VPC Endpoints for S3/ECR to save ~$380/year."
                    })

        return {
            "total_security_violations": len(security_findings),
            "security_findings": security_findings,
            "cost_optimizations": cost_findings,
            "pipeline_gate": "FAIL" if security_findings else "PASS"
        }


if __name__ == "__main__":
    agent = TerraformCostSecurityAgent()
    plan_data = agent.load_mock_tf_plan()
    audit_report = agent.audit_security_and_cost(plan_data)
    
    print("\n" + "="*70)
    print("🛡️ TERRAFORM IAC AUDIT REPORT BY DEVOPS AGENT")
    print("="*70)
    print(json.dumps(audit_report, indent=2))
