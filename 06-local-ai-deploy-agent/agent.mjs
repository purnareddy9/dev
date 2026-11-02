// ==============================================================
// Real-Time Local AI DevOps Deployment Agent
// Implements the ReAct (Reason + Act) Autonomous Loop on Windows
// Supports: Deploy, Self-Healing Conflict Test, Status, and Stop
// ==============================================================

import http from 'http';
import net from 'net';
import { spawn, execSync } from 'child_process';
import path from 'path';
import fs from 'fs';
import os from 'os';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// Terminal ANSI Color formatting
const colors = {
  reset: '\x1b[0m',
  bright: '\x1b[1m',
  blue: '\x1b[34m',
  magenta: '\x1b[35m',
  yellow: '\x1b[33m',
  green: '\x1b[32m',
  cyan: '\x1b[36m',
  red: '\x1b[31m',
};

// ==============================================================
// 1. TOOL REGISTRY (The Agent's "Hands")
// ==============================================================
const Tools = {
  async getSystemInfo() {
    return {
      os: `${os.type()} ${os.release()} (${os.arch()})`,
      nodeVersion: process.version,
      cpuCount: os.cpus().length,
      freeMemoryMB: Math.round(os.freemem() / 1024 / 1024),
      totalMemoryMB: Math.round(os.totalmem() / 1024 / 1024),
    };
  },

  async checkPort(port) {
    return new Promise((resolve) => {
      const socket = new net.Socket();
      socket.setTimeout(800);

      socket.on('connect', () => {
        socket.destroy();
        resolve({ available: false, message: `Port ${port} is currently OCCUPIED` });
      });

      socket.on('timeout', () => {
        socket.destroy();
        resolve({ available: true, message: `Port ${port} is AVAILABLE` });
      });

      socket.on('error', () => {
        resolve({ available: true, message: `Port ${port} is AVAILABLE` });
      });

      socket.connect(port, '127.0.0.1');
    });
  },

  async freePortOnWindows(port) {
    try {
      const netstatOutput = execSync(`netstat -ano | findstr :${port}`, { encoding: 'utf-8' });
      const lines = netstatOutput.trim().split('\n');
      const pids = new Set();

      for (const line of lines) {
        const parts = line.trim().split(/\s+/);
        const pid = parts[parts.length - 1];
        if (pid && !isNaN(pid) && pid !== '0') {
          pids.add(pid);
        }
      }

      if (pids.size === 0) {
        return { success: true, message: `No active processes found on port ${port}.` };
      }

      for (const pid of pids) {
        try {
          execSync(`taskkill /F /PID ${pid}`);
        } catch (_) {}
      }

      return { success: true, message: `Terminated process(es) holding port ${port}: PIDs ${Array.from(pids).join(', ')}` };
    } catch (err) {
      return { success: true, message: `Port ${port} is already cleared.` };
    }
  },

  async startApplication(appPath, port) {
    const fullAppPath = path.resolve(__dirname, appPath);
    if (!fs.existsSync(fullAppPath)) {
      throw new Error(`Application file not found at: ${fullAppPath}`);
    }

    const logFile = path.resolve(__dirname, 'app-runtime.log');
    const out = fs.openSync(logFile, 'a');
    const err = fs.openSync(logFile, 'a');

    const subprocess = spawn(process.execPath, [fullAppPath], {
      detached: true,
      stdio: ['ignore', out, err],
      env: { ...process.env, PORT: port.toString() },
      cwd: __dirname,
    });

    subprocess.unref();

    // Persist PID for tracking and cleanup
    fs.writeFileSync(path.resolve(__dirname, '.app.pid'), subprocess.pid.toString());

    return {
      success: true,
      pid: subprocess.pid,
      port,
      logFile,
      message: `Started application in background (PID: ${subprocess.pid})`,
    };
  },

  async verifyHealth(port, maxRetries = 5) {
    const url = `http://127.0.0.1:${port}/health`;
    
    for (let attempt = 1; attempt <= maxRetries; attempt++) {
      try {
        const result = await new Promise((resolve, reject) => {
          const req = http.get(url, { timeout: 1500 }, (res) => {
            let data = '';
            res.on('data', chunk => data += chunk);
            res.on('end', () => {
              if (res.statusCode === 200) {
                try {
                  resolve(JSON.parse(data));
                } catch {
                  resolve({ raw: data });
                }
              } else {
                reject(new Error(`HTTP Status ${res.statusCode}`));
              }
            });
          });

          req.on('error', reject);
          req.on('timeout', () => {
            req.destroy();
            reject(new Error('Connection timed out'));
          });
        });

        return { healthy: true, attempts: attempt, data: result };
      } catch (err) {
        if (attempt === maxRetries) {
          return { healthy: false, attempts: attempt, error: err.message };
        }
        await new Promise(r => setTimeout(r, 800));
      }
    }
  },

  async stopApplication() {
    const pidFile = path.resolve(__dirname, '.app.pid');
    if (fs.existsSync(pidFile)) {
      const pid = fs.readFileSync(pidFile, 'utf-8').trim();
      try {
        execSync(`taskkill /F /PID ${pid}`);
        fs.unlinkSync(pidFile);
        return { success: true, message: `Stopped application process PID: ${pid}` };
      } catch (e) {
        fs.unlinkSync(pidFile);
        return { success: true, message: `Process PID ${pid} was not running.` };
      }
    }
    return { success: true, message: "No tracked PID file found." };
  }
};

// ==============================================================
// 2. THE AI AGENT REASONING ENGINE (ReAct Loop)
// ==============================================================
class LocalDeploymentAgent {
  constructor(goal) {
    this.goal = goal;
    this.memory = [];
  }

  logHeader(title) {
    console.log(`\n${colors.bright}${colors.blue}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${colors.reset}`);
    console.log(`${colors.bright}${colors.cyan}🤖 AI AGENT: ${title}${colors.reset}`);
    console.log(`${colors.bright}${colors.blue}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${colors.reset}`);
  }

  thought(text) {
    console.log(`\n${colors.magenta}🧠 [THOUGHT]:${colors.reset} ${text}`);
    this.memory.push({ type: 'THOUGHT', content: text });
  }

  action(toolName, args) {
    console.log(`${colors.yellow}⚡ [ACTION]:${colors.reset} Calling tool ${colors.bright}\`${toolName}\`${colors.reset} with ${JSON.stringify(args)}`);
    this.memory.push({ type: 'ACTION', tool: toolName, args });
  }

  observation(result) {
    console.log(`${colors.green}👁️ [OBSERVATION]:${colors.reset} ${JSON.stringify(result, null, 2)}`);
    this.memory.push({ type: 'OBSERVATION', result });
  }

  finalReport(report) {
    console.log(`\n${colors.bright}${colors.green}═════════════════════════════════════════════════════════════════${colors.reset}`);
    console.log(`${colors.bright}${colors.green}🎉 DEPLOYMENT GOAL COMPLETED SUCCESSFULLY!${colors.reset}`);
    console.log(`${colors.bright}${colors.green}═════════════════════════════════════════════════════════════════${colors.reset}`);
    console.log(JSON.stringify(report, null, 2));
  }

  async run() {
    this.logHeader(`Objective: "${this.goal.description}"`);

    const targetPort = this.goal.port || 5050;
    const appPath = this.goal.appPath || 'sample-app/server.mjs';

    // Step 1: Discover Environment
    this.thought("First, I need to inspect the host machine environment to ensure prerequisites are satisfied.");
    this.action("getSystemInfo", {});
    const sysInfo = await Tools.getSystemInfo();
    this.observation(sysInfo);

    // Step 2: Check Port Status
    this.thought(`Now I must verify if target port ${targetPort} is available or if another process is holding it.`);
    this.action("checkPort", { port: targetPort });
    let portStatus = await Tools.checkPort(targetPort);
    this.observation(portStatus);

    // Step 3: Handle Port Conflict (Autonomous Self-Healing)
    if (!portStatus.available) {
      this.thought(`Port ${targetPort} is occupied! As an autonomous agent, I will remediate this by terminating the rogue process holding the port.`);
      this.action("freePortOnWindows", { port: targetPort });
      const freeResult = await Tools.freePortOnWindows(targetPort);
      this.observation(freeResult);

      // Re-verify port
      portStatus = await Tools.checkPort(targetPort);
      this.observation(portStatus);
    }

    // Step 4: Deploy & Launch Background Process
    this.thought(`Port ${targetPort} is free. Now I will launch the microservice (${appPath}) as a detached process.`);
    this.action("startApplication", { appPath, port: targetPort });
    const deployResult = await Tools.startApplication(appPath, targetPort);
    this.observation(deployResult);

    // Step 5: Verification & Health Check Loop
    this.thought(`The application process is spawned with PID ${deployResult.pid}. Now I must probe http://127.0.0.1:${targetPort}/health to ensure it is passing health checks.`);
    this.action("verifyHealth", { port: targetPort, maxRetries: 5 });
    const healthResult = await Tools.verifyHealth(targetPort);
    this.observation(healthResult);

    if (!healthResult.healthy) {
      throw new Error(`Deployment verification failed: Service on port ${targetPort} did not respond with 200 OK.`);
    }

    // Step 6: Formulate Final State
    this.thought("Health check returned HTTP 200 OK with healthy status. The service is active and responding. Goal accomplished.");
    
    this.finalReport({
      status: "DEPLOYED",
      service: "payment-mock-service",
      pid: deployResult.pid,
      url: `http://127.0.0.1:${targetPort}`,
      healthEndpoint: `http://127.0.0.1:${targetPort}/health`,
      metricsEndpoint: `http://127.0.0.1:${targetPort}/metrics`,
      systemDetails: sysInfo,
      deploymentLog: deployResult.logFile
    });
  }
}

// ==============================================================
// 3. CLI ROUTER
// ==============================================================
const command = process.argv[2] || 'deploy';

if (command === 'stop') {
  console.log(`${colors.yellow}Stopping application...${colors.reset}`);
  Tools.stopApplication().then(res => console.log(res.message));
} else if (command === 'status') {
  Tools.verifyHealth(5050, 1).then(res => {
    if (res.healthy) {
      console.log(`${colors.green}Service is RUNNING and HEALTHY:${colors.reset}`, res.data);
    } else {
      console.log(`${colors.red}Service is NOT RUNNING on port 5050.${colors.reset}`);
    }
  });
} else {
  const agent = new LocalDeploymentAgent({
    description: "Deploy sample Node.js payment microservice locally on Windows, verify healthcheck, and report runtime status.",
    port: 5050,
    appPath: "sample-app/server.mjs"
  });

  agent.run().catch(err => {
    console.error(`\n${colors.bright}${colors.red}❌ DEPLOYMENT FAILED: ${err.message}${colors.reset}`);
    process.exit(1);
  });
}
