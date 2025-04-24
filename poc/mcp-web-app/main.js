/* main.js – multi-server, stdio transport */
require("dotenv").config();
const { app, BrowserWindow, ipcMain, dialog } = require("electron");
const path = require("path");
const fs = require("fs");
const spawn = require("cross-spawn");
const axios = require("axios"); // ← OpenAI용
const portfinder = require("portfinder"); // 다른 서버용
const { v4: uuid } = require("uuid");

/* ───── logger ───── */
const ts = () => new Date().toISOString();
const log = (...a) => console.log(ts(), "[INFO ]", ...a);
const warn = (...a) => console.warn(ts(), "[WARN ]", ...a);
const err = (...a) => console.error(ts(), "[ERROR]", ...a);

/* ───── Stdio RPC helper ───── */
class StdioRPCClient {
  constructor(proc, tag) {
    this.proc = proc;
    this.tag = tag;
    this.pending = new Map();
    this.buffer = "";
    proc.stdout.on("data", (d) => this.#onData(d));
    proc.stderr.on("data", (d) =>
      d
        .toString()
        .split(/\r?\n/)
        .forEach((l) => {
          if (!l) return;
          if (l.startsWith("Secure MCP") || l.startsWith("Allowed"))
            log(`[${this.tag}]`, l);
          else err(`[${this.tag}!]`, l);
        })
    );
    proc.on("exit", (c) => warn(`[${tag}] exited`, c));
  }
  #onData(chunk) {
    this.buffer += chunk.toString();
    let idx;
    while ((idx = this.buffer.indexOf("\n")) >= 0) {
      const line = this.buffer.slice(0, idx).trim();
      this.buffer = this.buffer.slice(idx + 1);
      if (!line) continue;
      try {
        const msg = JSON.parse(line);
        const p = this.pending.get(msg.id);
        if (p) {
          this.pending.delete(msg.id);
          msg.error ? p.reject(msg.error) : p.resolve(msg.result);
        }
      } catch (e) {
        err(`[${this.tag}] broken JSON`, line);
      }
    }
  }
  call(method, params = {}) {
    const id = uuid();
    const payload = { jsonrpc: "2.0", id, method, params };
    return new Promise((resolve, reject) => {
      this.pending.set(id, { resolve, reject });
      this.proc.stdin.write(JSON.stringify(payload) + "\n");
    });
  }
}

/* ───── 0. server definitions ───── */
const SERVER_DEFS = [
  {
    id: "fs",
    name: "Filesystem",
    bin:
      process.platform === "win32"
        ? "mcp-server-filesystem.cmd"
        : "mcp-server-filesystem",
    allowedDir: process.cwd(),
  },
];

/* ───── 1. runtime state ───── */
const servers = []; // {id,name,proc,rpc,tools,allowedDir}

/* ───── 2. spawn & load tools ───── */
async function spawnServer(def) {
  const binPath = path.join(__dirname, "node_modules", ".bin", def.bin);
  if (!fs.existsSync(binPath)) {
    err("not found", binPath);
    return null;
  }
  log(`Spawning ${def.id}`, binPath, def.allowedDir);
  const proc = spawn(binPath, [def.allowedDir], {
    cwd: def.allowedDir,
    stdio: ["pipe", "pipe", "pipe"],
  });
  const rpc = new StdioRPCClient(proc, def.id);

  const srv = { ...def, proc, rpc, tools: [] };
  await refreshTools(srv);
  servers.push(srv);
  aliasMap.clear();
  return srv;
}
async function refreshTools(srv) {
  try {
    // ① list_tools → ② tools/list 순서로 시도
    let raw = null;
    try {
      raw = await srv.rpc.call("list_tools");
    } catch (e) {
      raw = await srv.rpc.call("tools/list");
    }

    // ② 형식 정규화 : 배열? 객체? 중첩?
    let arr = [];
    if (Array.isArray(raw)) arr = raw;
    else if (raw?.tools) arr = raw.tools;
    else if (typeof raw === "object") arr = Object.values(raw);

    if (!arr.length) throw new Error("no tools found");
    srv.tools = arr.map((t) => ({
      ...t,
      name: `${srv.id}_${t.name}`, // <-- dot → underscore
      _origMethod: t.name, //   원본 이름 보관
    }));
    log(
      `Tools[${srv.id}] loaded`,
      srv.tools.map((t) => t.name)
    );
  } catch (e) {
    err("tool load failed", e.message);
  }
}
function allTools() {
  return servers.flatMap((s) => s.tools);
}

function formatToolV2(t) {
  // t             : { name, description, parameters|inputSchema, _origMethod }
  // t.name        : safe alias명  (fs_read_file)
  // t._origMethod : 서버측 실제 method (read_file)
  aliasMap.set(t.name, {
    srvId: t.name.split("_", 1)[0],
    method: t._origMethod,
  });

  return {
    type: "function",
    function: {
      name: t.name,
      description: t.description,
      parameters: t.inputSchema || // 서버 v0.3
        t.parameters || {
          // 다른 서버 혹시
          type: "object",
          properties: {},
        },
    },
  };
}

const aliasMap = new Map();

/* ───── 3. OpenAI decision ───── */
async function decideCall(prompt) {
  const key = process.env.OPENAI_API_KEY;
  if (!key) return { type: "text", content: "OPENAI_API_KEY is not set." };

  const res = await axios.post(
    "https://api.openai.com/v1/chat/completions",
    {
      model: "gpt-4o-mini",
      messages: [
        {
          role: "system",
          content: `
You are a specialized agent that transforms user requests into calls to the registered filesystem tools, or else returns plain-text answers.

Guidelines:
1. TOOL CALL
   • If a request requires filesystem access (reading, writing, listing, etc.), emit exactly one tool call JSON with the correct tool name and all required parameters.
   • Use only the provided tool names and schemas—do not invent new tools or free-form code.
   • If the user did not specify a path (or uses "/" or "."), use the current project root directory instead.
2. TEXT RESPONSE
   • If the request can be satisfied without filesystem access, reply with natural-language text and do not call any tool.  
3. FOLLOW-UP QUESTIONS
   • If a required parameter is missing or ambiguous, ask the user a clarifying question instead of guessing.  
4. NO EXTRA VERBIAGE
   • When calling a tool, respond with strictly the function call object—no explanatory text.
   • Any human-readable explanation should only appear in plain-text responses when no tool is invoked.
`,
        },
        { role: "user", content: prompt },
      ],
      tools: allTools().map(formatToolV2),
      tool_choice: "auto",
      max_tokens: 1024,
    },
    { headers: { Authorization: `Bearer ${key}` } }
  );
  log("[LLM] raw response:", JSON.stringify(res.data, null, 2));

  const msg = res.data.choices[0].message;

  // ── v2 호출: tool_calls[n].function.name/arguments
  let fc = null;
  if (Array.isArray(msg.tool_calls) && msg.tool_calls.length > 0) {
    fc = msg.tool_calls[0].function;
  }
  // ── legacy v1 호출: function_call.name/arguments
  else if (msg.function_call) {
    fc = msg.function_call;
  }

  // 호출 정보가 없거나 arguments 가 비어 있으면 텍스트 응답
  if (!fc || !fc.arguments) {
    return { type: "text", content: msg.content ?? "" };
  }

  // JSON parsing
  let parsed;
  try {
    parsed = JSON.parse(fc.arguments);
  } catch (e) {
    err("Failed to parse tool arguments:", fc.arguments);
    return { type: "text", content: msg.content ?? "" };
  }

  const alias = fc.name; // e.g. "fs_directory_tree"
  const params = parsed.params || parsed;

  const map = aliasMap.get(alias);
  if (!map) {
    err("Unmapped tool alias:", alias);
    return { type: "text", content: msg.content ?? "" };
  }

  return {
    type: "rpc",
    srvId: map.srvId,
    method: map.method,
    params,
  };
}

/* ───── 4. Electron window ───── */
let mainWindow;
function createWindow() {
  log("createWindow");
  mainWindow = new BrowserWindow({
    width: 1000,
    height: 700,
    webPreferences: {
      preload: path.join(__dirname, "preload.js"),
      contextIsolation: true,
    },
  });
  mainWindow.loadFile(path.join(__dirname, "renderer", "index.html"));
}

/* ───── 5. IPC ───── */
ipcMain.handle("select-folder", async () => {
  const r = await dialog.showOpenDialog({ properties: ["openDirectory"] });
  if (r.canceled) return null;
  const dir = r.filePaths[0];
  log("folder selected", dir);

  // 재시작
  const idx = servers.findIndex((s) => s.id === "fs");
  if (idx >= 0) {
    servers[idx].proc.kill();
    servers.splice(idx, 1);
  }
  await spawnServer({ ...SERVER_DEFS[0], allowedDir: dir });
  return dir;
});
ipcMain.handle("run-command", async (_e, prompt) => {
  log("[IPC] run-command", prompt);
  try {
    // 1) LLM 결정 → RPC 호출
    const d = await decideCall(prompt);
    if (d.type === "text") {
      // → 그냥 텍스트 리턴 (post-process 없이)
      return { result: d.content };
    }

    const srv = servers.find((s) => s.id === d.srvId);
    if (!srv) throw new Error(`server ${d.srvId} not found`);

    const payload = { name: d.method, arguments: d.params };
    log("[RPC] calling call_tool", payload);

    // 2) 실제 MCP 서버 호출
    let rpcRes;
    try {
      rpcRes = await srv.rpc.call("call_tool", payload);
    } catch (err) {
      if (err.code === -32601) {
        log("[RPC] call_tool not found, falling back to tools/call");
        rpcRes = await srv.rpc.call("tools/call", payload);
      } else {
        throw err;
      }
    }

    // 3) 툴 호출 결과에서 text만 꺼내기
    let rawResult;
    if (rpcRes && Array.isArray(rpcRes.content)) {
      rawResult = rpcRes.content
        .filter((c) => c.type === "text" && typeof c.text === "string")
        .map((c) => c.text)
        .join("\n");
    } else {
      rawResult = JSON.stringify(rpcRes);
    }
    log("[RPC] rawResult:", rawResult);

    // ──────────────────────────────────────────────────────────
    // 4) → 여기서 다시 LLM에 보내서 자연어 응답 생성
    const postRes = await axios.post(
      "https://api.openai.com/v1/chat/completions",
      {
        model: "gpt-4o-mini",
        messages: [
          {
            role: "system",
            content:
              "You are a helpful assistant. The user made a request, " +
              "we ran a filesystem tool and got some raw output. " +
              "Now produce a single, concise, natural-language response " +
              "that explains the result to the user." + 
              "답변은 한글로 해주세요",
          },
          { role: "user", content: `Original request:\n${prompt}` },
          { role: "assistant", content: `Tool output:\n${rawResult}` },
        ],
        max_tokens: 512,
      },
      { headers: { Authorization: `Bearer ${process.env.OPENAI_API_KEY}` } }
    );

    const friendly = postRes.data.choices[0].message.content.trim();
    log("[POST-PROCESS] final friendly answer:", friendly);

    return { result: friendly };
  } catch (e) {
    err("cmd fail", e);
    return { error: e.message };
  }
});


/* ───── 6. lifecycle ───── */
app.whenReady().then(async () => {
  log("Electron ready");
  for (const def of SERVER_DEFS) await spawnServer(def);
  createWindow();
});
app.on("will-quit", () => servers.forEach((s) => s.proc.kill()));
