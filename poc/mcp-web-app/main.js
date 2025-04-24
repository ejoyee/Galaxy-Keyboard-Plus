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
        { role: "system", content: "You are an agent…" },
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
    const d = await decideCall(prompt);
    if (d.type === "text") return { result: d.content };

    const srv = servers.find((s) => s.id === d.srvId);
    if (!srv) throw new Error(`server ${d.srvId} not found`);

    // 툴 호출 페이로드
    const payload = { name: d.method, arguments: d.params };
    log("[RPC] calling call_tool", payload);

    let rpcRes;
    try {
      // 먼저 call_tool 시도
      rpcRes = await srv.rpc.call("call_tool", payload);
    } catch (err) {
      if (err.code === -32601) {
        // call_tool 이 없으면 tools/call 로 재시도
        log("[RPC] call_tool not found, falling back to tools/call");
        rpcRes = await srv.rpc.call("tools/call", payload);
      } else throw err;
    }
    // ───────────────────────────────────────────────
    // 툴 호출 결과가 { content: [ { type:'text', text } ] } 형태라면
    // text 필드만 꺼내서 하나의 문자열로 만든다.
    let result;
    if (rpcRes && Array.isArray(rpcRes.content)) {
      const texts = rpcRes.content
        .filter((c) => c.type === "text" && typeof c.text === "string")
        .map((c) => c.text);
      result = texts.join("\n");
    } else {
      // 그 외엔 그냥 있는 그대로
      result = rpcRes;
    }
    log(`[RPC] final result:`, result);
    return { result };
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
