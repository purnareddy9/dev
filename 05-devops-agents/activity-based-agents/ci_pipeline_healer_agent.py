"""
==============================================================================
Activity Agent 1: CI/CD Pipeline Healing Agent
==============================================================================
Automates:
1. Ingesting failed GitHub Actions / Jenkins build logs.
2. Isolating the exact failure stacktrace / compiler error.
3. Diagnosing root cause (missing dep, syntax error, broken test).
4. Generating code patch and opening an automated Pull Request.
==============================================================================
"""

import json
import re
from typing import Dict, Any, List

class CIPipelineHealerAgent:
    """Agent that heals broken CI/CD pipelines automatically."""

    def __init__(self, repo: str, run_id: int):
        self.repo = repo
        self.run_id = run_id

    def fetch_failed_build_log(self) -> str:
        """Simulates fetching stdout/stderr log of the failed job."""
        return """
        [INFO] Running npm test suite...
        PASS src/utils.test.ts
        FAIL src/auth/jwt.test.ts
        ● Authentication › Token Verification › should reject expired tokens
            TypeError: Cannot read properties of undefined (reading 'split')
              at Object.verifyToken (src/auth/jwt.ts:42:28)
              at Object.<anonymous> (src/auth/jwt.test.ts:18:25)
              
        Tests: 1 failed, 1 passed, 2 total
        Error: Process completed with exit code 1.
        """

    def fetch_source_file(self, file_path: str) -> str:
        """Simulates retrieving the offending source code via GitHub API."""
        return """
        // src/auth/jwt.ts
        export function verifyToken(authHeader: string | undefined): boolean {
            // BUG: authHeader can be undefined, causing split() to crash!
            const token = authHeader.split(' ')[1];
            return jwt.verify(token, process.env.JWT_SECRET!);
        }
        """

    def extract_failure_context(self, raw_log: str) -> Dict[str, Any]:
        """Filters out non-essential log noise and extracts the culprit file and line."""
        print("🔍 [STEP 1]: Parsing raw CI log buffer for errors...")
        
        # Regex to locate standard stacktraces: file.ts:line:column
        match = re.search(r'at .* \((.+):(\d+):(\d+)\)', raw_log)
        error_msg = re.search(r'TypeError: (.+)', raw_log)
        
        file_path = match.group(1) if match else "unknown"
        line_num = int(match.group(2)) if match else 0
        reason = error_msg.group(1) if error_msg else "Unknown assertion failure"

        return {
            "culprit_file": file_path,
            "line_number": line_num,
            "error_type": "TypeError",
            "message": reason
        }

    def reason_and_patch(self, failure_info: Dict[str, Any], source_code: str) -> Dict[str, Any]:
        """Agent Reasoning Loop: Synthesizes a bug fix."""
        print(f"🧠 [STEP 2]: Analyzing bug in `{failure_info['culprit_file']}` at line {failure_info['line_number']}...")
        
        # Proposed fix: Add optional chaining and null check for authHeader
        proposed_patch = """
        // src/auth/jwt.ts (HEALED)
        export function verifyToken(authHeader: string | undefined): boolean {
            if (!authHeader || !authHeader.startsWith('Bearer ')) {
                return false;
            }
            const token = authHeader.split(' ')[1];
            return jwt.verify(token, process.env.JWT_SECRET!);
        }
        """

        return {
            "analysis": "Function `verifyToken` assumes `authHeader` is always defined. When an unauthenticated request arrives, `authHeader.split` crashes with TypeError.",
            "fix_strategy": "Add defensive guard clause checking for existence and 'Bearer ' prefix.",
            "diff": proposed_patch
        }

    def create_automated_pr(self, patch_data: Dict[str, Any], failure_info: Dict[str, Any]) -> Dict[str, Any]:
        """Simulates creating a Git branch, committing the patch, and opening a PR."""
        print("🚀 [STEP 3]: Submitting automated fix PR to GitHub...")
        branch_name = f"agent/fix-ci-run-{self.run_id}"
        
        pr_payload = {
            "title": f"🤖 [AI-Heal] Fix {failure_info['error_type']} in {failure_info['culprit_file']}",
            "branch": branch_name,
            "base": "main",
            "body": (
                f"### Automated CI Healing Report\n\n"
                f"**Triggering Run**: [CI Run #{self.run_id}](https://github.com/{self.repo}/actions/runs/{self.run_id})\n"
                f"**Root Cause**: {patch_data['analysis']}\n\n"
                f"**Applied Fix**:\n```typescript\n{patch_data['diff']}\n```\n\n"
                f"---\n*Generated autonomously by DevOps CI Healer Agent*"
            ),
            "status": "OPEN",
            "pr_url": f"https://github.com/{self.repo}/pull/105"
        }
        return pr_payload

    def execute(self) -> Dict[str, Any]:
        raw_log = self.fetch_failed_build_log()
        failure_info = self.extract_failure_context(raw_log)
        source_code = self.fetch_source_file(failure_info["culprit_file"])
        patch_data = self.reason_and_patch(failure_info, source_code)
        pr_result = self.create_automated_pr(patch_data, failure_info)
        return pr_result


if __name__ == "__main__":
    agent = CIPipelineHealerAgent(repo="purnareddy9/auth-service", run_id=98214)
    result = agent.execute()
    print("\n" + "="*70)
    print("📋 AUTOMATED HEALING SUMMARY")
    print("="*70)
    print(json.dumps(result, indent=2))
