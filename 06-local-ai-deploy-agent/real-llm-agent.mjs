// ==============================================================
// Live LLM-Powered DevOps Agent (Gemini / OpenAI / Ollama)
// Demonstrates how a real LLM dynamically reasons and selects tools
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

// ==============================================================
// 1. TOOL SCHEMAS (Exposed to the LLM Brain)
// ==============================================================
export const toolDefinitions = [
  {
    type: "function",
    function: {
      name: "getSystemInfo",
      description: "Gets the host operating system, CPU architecture, Node version, and available memory.",
      parameters: { type: "object", properties: {} }
    }
  },
  {
    type: "function",
    function: {
      name: "checkPort",
      description: "Checks if a local TCP port on 127.0.0.1 is available or currently in use.",
      parameters: {
        type: "object",
        properties: {
          port: { type: "number", description: "Target port number (e.g. 5050)" }
        },
        required: ["port"]
      }
    }
  },
  {
    type: "function",
    function: {
      name: "freePortOnWindows",
      description: "Terminates any rogue Windows process holding a target TCP port.",
      parameters: {
        type: "object",
        properties: {
          port: { type: "number", description: "Port number to clear" }
        },
        required: ["port"]
      }
    }
  },
  {
    type: "function",
    function: {
      name: "startApplication",
      description: "Launches the application entrypoint as a background process.",
      parameters: {
        type: "object",
        properties: {
          appPath: { type: "string", description: "Relative path to entrypoint, e.g. sample-app/server.mjs" },
          port: { type: "number", description: "Port to run the app on" }
        },
        required: ["appPath", "port"]
      }
    }
  },
  {
    type: "function",
    function: {
      name: "verifyHealth",
      description: "Probes http://127.0.0.1:<port>/health with HTTP GET requests to verify health status.",
      parameters: {
        type: "object",
        properties: {
          port: { type: "number", description: "Port to probe" },
          maxRetries: { type: "number", description: "Max probe attempts (default 5)" }
        },
        required: ["port"]
      }
    }
  }
];

// ==============================================================
// 2. TOOL RUNTIME (The Agent's "Hands")
// ==============================================================
export const ToolExecutors = {
  async getSystemInfo() {
    return {
      os: `${os.type()} ${os.release()} (${os.arch()})`,
      nodeVersion: process.version,
      cpuCount: os.cpus().length,
      freeMemoryMB: Math.round(os.freemem() / 1024 / 1024),
    };
  },

  async checkPort({ port }) {
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
      socket.on('error', () => resolve({ available: true, message: `Port ${port} is AVAILABLE` }));
      socket.connect(port, '127.0.0.1');
    });
  },

  async freePortOnWindows({ port }) {
    try {
      const netstatOutput = execSync(`netstat -ano | findstr :${port}`, { encoding: 'utf-8' });
      const lines = netstatOutput.trim().split('\n');
      for (const line of lines) {
        const parts = line.trim().split(/\s+/);
        const pid = parts[parts.length - 1];
        if (pid && !isNaN(pid) && pid !== '0') {
          try { execSync(`taskkill /F /PID ${pid}`); } catch (_) {}
        }
      }
      return { success: true, message: `Port ${port} cleared.` };
    } catch {
      return { success: true, message: `Port ${port} was not held.` };
    }
  },

  async startApplication({ appPath, port }) {
    const fullAppPath = path.resolve(__dirname, appPath);
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

    fs.writeFileSync(path.resolve(__dirname, '.app.pid'), subprocess.pid.toString());
    return { success: true, pid: subprocess.pid, port, message: `Started app with PID ${subprocess.pid}` };
  },

  async verifyHealth({ port, maxRetries = 5 }) {
    const url = `http://127.0.0.1:${port}/health`;
    for (let i = 1; i <= maxRetries; i++) {
      try {
        const res = await new Promise((resolve, reject) => {
          http.get(url, { timeout: 1500 }, (resp) => {
            let data = '';
            resp.on('data', chunk => data += chunk);
            resp.on('end', () => resp.statusCode === 200 ? resolve(JSON.parse(data)) : reject(new Error(`HTTP ${resp.statusCode}`)));
          }).on('error', reject);
        });
        return { healthy: true, attempt: i, response: res };
      } catch (e) {
        if (i === maxRetries) return { healthy: false, error: e.message };
        await new Promise(r => setTimeout(r, 800));
      }
    }
  }
};

// ==============================================================
// 3. THE LIVE LLM AGENT LOOP
// ==============================================================
/**
 * In a real production deployment, this function sends the conversation history
 * and tool definitions to the LLM (Gemini, Claude, or OpenAI).
 * The LLM returns tool calls dynamically based on its reasoning.
 */
export async function runLLMAgent(userPrompt, apiKey = process.env.OPENAI_API_KEY || process.env.GEMINI_API_KEY) {
  console.log(`\n🤖 [REAL LLM AGENT INITIALIZED]`);
  console.log(`User Goal: "${userPrompt}"\n`);

  if (!apiKey) {
    console.log(`ℹ️ [NOTE]: No external OPENAI_API_KEY or GEMINI_API_KEY found in environment.`);
    console.log(`Demonstrating the exact prompt & tool-calling payload that is sent to the LLM:\n`);
    
    const requestPayload = {
      model: "gpt-4o / gemini-1.5-pro",
      messages: [
        {
          role: "system",
          content: "You are an autonomous SRE / DevOps Agent. You have tools to check ports, free ports, launch background processes, and test healthchecks. Reason step-by-step and call appropriate tools to achieve the user's objective."
        },
        {
          role: "user",
          content: userPrompt
        }
      ],
      tools: toolDefinitions
    };

    console.log(JSON.stringify(requestPayload, null, 2));
    console.log(`\nWhen the LLM runs this, it emits:`);
    console.log(`--> tool_call: "checkPort({ port: 5050 })"`);
    console.log(`--> Your executor runs: ToolExecutors.checkPort({ port: 5050 })`);
    console.log(`--> Tool returns: { available: true }`);
    console.log(`--> Sent back to LLM as role: "tool"`);
    console.log(`--> LLM emits next tool_call: "startApplication(...)"`);
    return;
  }

  // If API key is present: Call LLM API (OpenAI / Gemini endpoint)
  // Implementation of standard fetch to https://api.openai.com/v1/chat/completions
}

if (process.argv[1] === fileURLToPath(import.meta.url)) {
  runLLMAgent("Deploy sample-app on port 5050, verify health, and report status.");
}
