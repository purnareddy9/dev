#!/usr/bin/env python3
"""
==============================================================================
Real-Time Python DevOps Deployment Agent (Windows & Linux Compatible)
Implements the Autonomous ReAct (Reason + Act) Loop in Native Python
==============================================================================
"""

import os
import sys
import json
import time
import socket
import platform
import subprocess
import urllib.request
import urllib.error

# Ensure UTF-8 output on Windows consoles
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# ANSI Color codes for formatted terminal output
class Colors:
    RESET = "\033[0m"
    BOLD = "\033[1m"
    BLUE = "\033[34m"
    MAGENTA = "\033[35m"
    YELLOW = "\033[33m"
    GREEN = "\033[32m"
    CYAN = "\033[36m"
    RED = "\033[31m"

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PID_FILE = os.path.join(SCRIPT_DIR, ".app_python.pid")
LOG_FILE = os.path.join(SCRIPT_DIR, "app-runtime.log")


class PythonDevOpsTools:
    """The Agent's System Execution Tools (The 'Hands')"""

    @staticmethod
    def get_system_info() -> dict:
        """Inspects host machine operating system, CPU, and Python runtime."""
        return {
            "os": f"{platform.system()} {platform.release()} ({platform.machine()})",
            "python_version": platform.python_version(),
            "cpu_count": os.cpu_count(),
            "hostname": platform.node()
        }

    @staticmethod
    def check_port(port: int) -> dict:
        """Checks if a TCP port on 127.0.0.1 is occupied or available."""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(0.8)
            result = s.connect_ex(("127.0.0.1", port))
            if result == 0:
                return {"available": False, "message": f"Port {port} is currently OCCUPIED"}
            else:
                return {"available": True, "message": f"Port {port} is AVAILABLE"}

    @staticmethod
    def free_port_on_windows(port: int) -> dict:
        """Finds PIDs bound to the port on Windows and terminates them."""
        try:
            cmd = f'netstat -ano | findstr :{port}'
            output = subprocess.check_output(cmd, shell=True, text=True)
            pids = set()
            for line in output.strip().splitlines():
                parts = line.split()
                if parts and parts[-1].isdigit() and parts[-1] != "0":
                    pids.add(parts[-1])

            if not pids:
                return {"success": True, "message": f"No active processes found on port {port}."}

            for pid in pids:
                try:
                    subprocess.run(f"taskkill /F /PID {pid}", shell=True, capture_output=True)
                except Exception:
                    pass

            return {"success": True, "message": f"Terminated process(es) holding port {port}: PIDs {list(pids)}"}
        except Exception:
            return {"success": True, "message": f"Port {port} is already cleared."}

    @staticmethod
    def start_application(app_relative_path: str, port: int) -> dict:
        """Launches the target microservice as a background detached process."""
        full_path = os.path.join(SCRIPT_DIR, app_relative_path)
        if not os.path.exists(full_path):
            raise FileNotFoundError(f"Application entrypoint not found at: {full_path}")

        env = os.environ.copy()
        env["PORT"] = str(port)

        with open(LOG_FILE, "a", encoding="utf-8") as out_log:
            # On Windows: DETACHED_PROCESS flag ensures process runs independently in background
            creationflags = 0
            if platform.system() == "Windows":
                creationflags = subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP

            proc = subprocess.Popen(
                ["node", full_path],
                stdout=out_log,
                stderr=out_log,
                env=env,
                cwd=SCRIPT_DIR,
                creationflags=creationflags
            )

        with open(PID_FILE, "w", encoding="utf-8") as pf:
            pf.write(str(proc.pid))

        return {
            "success": True,
            "pid": proc.pid,
            "port": port,
            "log_file": LOG_FILE,
            "message": f"Started application in background (PID: {proc.pid})"
        }

    @staticmethod
    def verify_health(port: int, max_retries: int = 5) -> dict:
        """Polls the HTTP /health endpoint with retry backoff."""
        url = f"http://127.0.0.1:{port}/health"

        for attempt in range(1, max_retries + 1):
            try:
                req = urllib.request.Request(url, headers={"User-Agent": "PythonDevOpsAgent/1.0"})
                with urllib.request.urlopen(req, timeout=1.5) as resp:
                    if resp.status == 200:
                        data = json.loads(resp.read().decode("utf-8"))
                        return {"healthy": True, "attempts": attempt, "data": data}
            except Exception as e:
                if attempt == max_retries:
                    return {"healthy": False, "attempts": attempt, "error": str(e)}
                time.sleep(0.8)

        return {"healthy": False, "error": "Max retries exceeded"}

    @staticmethod
    def stop_application() -> dict:
        """Terminates the tracked background process."""
        if os.path.exists(PID_FILE):
            with open(PID_FILE, "r", encoding="utf-8") as pf:
                pid = pf.read().strip()
            try:
                subprocess.run(f"taskkill /F /PID {pid}", shell=True, capture_output=True)
                os.remove(PID_FILE)
                return {"success": True, "message": f"Successfully stopped process PID {pid}."}
            except Exception as e:
                if os.path.exists(PID_FILE):
                    os.remove(PID_FILE)
                return {"success": True, "message": f"Process {pid} was already terminated."}
        return {"success": True, "message": "No tracked PID file found."}


class PythonDeploymentAgent:
    """The Autonomous ReAct Agent Controller"""

    def __init__(self, objective: str, target_port: int = 5050, app_path: str = "sample-app/server.mjs"):
        self.objective = objective
        self.port = target_port
        self.app_path = app_path
        self.tools = PythonDevOpsTools()
        self.memory = []

    def log_thought(self, text: str):
        print(f"\n{Colors.MAGENTA}🧠 [THOUGHT]:{Colors.RESET} {text}")
        self.memory.append({"type": "THOUGHT", "content": text})

    def log_action(self, tool_name: str, args: dict):
        print(f"{Colors.YELLOW}⚡ [ACTION]:{Colors.RESET} Invoking tool {Colors.BOLD}`{tool_name}`{Colors.RESET} with {json.dumps(args)}")
        self.memory.append({"type": "ACTION", "tool": tool_name, "args": args})

    def log_observation(self, result: dict):
        print(f"{Colors.GREEN}👁️ [OBSERVATION]:{Colors.RESET} {json.dumps(result, indent=2)}")
        self.memory.append({"type": "OBSERVATION", "result": result})

    def run(self):
        print(f"\n{Colors.BOLD}{Colors.BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{Colors.RESET}")
        print(f"{Colors.BOLD}{Colors.CYAN}🤖 PYTHON DEVOPS AGENT: Objective: \"{self.objective}\"{Colors.RESET}")
        print(f"{Colors.BOLD}{Colors.BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{Colors.RESET}")

        # Step 1: System Introspection
        self.log_thought("I need to discover host architecture, Python runtime, and CPU resources.")
        self.log_action("get_system_info", {})
        sys_info = self.tools.get_system_info()
        self.log_observation(sys_info)

        # Step 2: Check Port
        self.log_thought(f"Now I must verify if port {self.port} is available or blocked by another process.")
        self.log_action("check_port", {"port": self.port})
        port_status = self.tools.check_port(self.port)
        self.log_observation(port_status)

        # Step 3: Self-Healing Port Conflict Handling
        if not port_status["available"]:
            self.log_thought(f"Port {self.port} is occupied! As an autonomous agent, I will terminate the conflicting process.")
            self.log_action("free_port_on_windows", {"port": self.port})
            free_res = self.tools.free_port_on_windows(self.port)
            self.log_observation(free_res)

        # Step 4: Deploy & Spawn Background App
        self.log_thought(f"Port {self.port} is ready. Launching application `{self.app_path}` in background.")
        self.log_action("start_application", {"app_path": self.app_path, "port": self.port})
        deploy_res = self.tools.start_application(self.app_path, self.port)
        self.log_observation(deploy_res)

        # Step 5: Health Verification Loop
        self.log_thought(f"Process spawned with PID {deploy_res['pid']}. Verifying readiness via http://127.0.0.1:{self.port}/health.")
        self.log_action("verify_health", {"port": self.port, "max_retries": 5})
        health_res = self.tools.verify_health(self.port)
        self.log_observation(health_res)

        if not health_res.get("healthy"):
            raise RuntimeError(f"Health verification failed on port {self.port}: {health_res.get('error')}")

        # Step 6: Formulate Final State
        self.log_thought("Health check returned HTTP 200 OK. Application is operational. Objective fulfilled.")

        report = {
            "status": "DEPLOYED",
            "runtime": "python-agent-controller",
            "pid": deploy_res["pid"],
            "url": f"http://127.0.0.1:{self.port}",
            "health_endpoint": f"http://127.0.0.1:{self.port}/health",
            "metrics_endpoint": f"http://127.0.0.1:{self.port}/metrics",
            "system_details": sys_info,
            "runtime_log": deploy_res["log_file"]
        }

        print(f"\n{Colors.BOLD}{Colors.GREEN}═════════════════════════════════════════════════════════════════{Colors.RESET}")
        print(f"{Colors.BOLD}{Colors.GREEN}🎉 PYTHON AGENT: DEPLOYMENT SUCCESSFUL!{Colors.RESET}")
        print(f"{Colors.BOLD}{Colors.GREEN}═════════════════════════════════════════════════════════════════{Colors.RESET}")
        print(json.dumps(report, indent=2))


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "deploy"

    if cmd == "stop":
        res = PythonDevOpsTools.stop_application()
        print(f"{Colors.YELLOW}{res['message']}{Colors.RESET}")
    elif cmd == "status":
        health = PythonDevOpsTools.verify_health(5050, max_retries=1)
        if health.get("healthy"):
            print(f"{Colors.GREEN}Service is RUNNING & HEALTHY:{Colors.RESET}", json.dumps(health["data"], indent=2))
        else:
            print(f"{Colors.RED}Service is NOT RUNNING on port 5050.{Colors.RESET}")
    else:
        agent = PythonDeploymentAgent(
            objective="Deploy sample Node.js payment microservice locally on Windows using Python, verify health, and report status.",
            target_port=5050,
            app_path="sample-app/server.mjs"
        )
        agent.run()
