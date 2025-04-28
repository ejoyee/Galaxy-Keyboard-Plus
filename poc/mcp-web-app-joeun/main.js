/**
 * @typedef {Object} ToolCall
 * @property {string} name - MCP tool 이름 (예: gdrive_read_file_content)
 * @property {Object.<string, any>} arguments - 툴 인자
 */

/**
 * @typedef {Object} ExecutionContext
 * @property {any} [previousResult] - 바로 직전 tool의 결과
 * @property {any[]} results - 모든 tool 실행 결과
 */

/* ───────────── OAuth 관련 함수 ───────────── */
// OAuth 설정 파일 경로
const path = require("path");
const fs = require("fs");
const HOME_DIR = process.env.HOME || process.env.USERPROFILE;
const CONFIG_DIR = path.join(HOME_DIR, ".gmail-mcp");
const OAUTH_PATH = path.join(CONFIG_DIR, "gcp-oauth.keys.json");
const CREDENTIALS_PATH = path.join(CONFIG_DIR, "credentials.json");

// OAuth 클라이언트 설정 (발급자용 설정 활용)
const OAUTH_CLIENT_ID = "707596761486-2nanfg75jmj5c05jqndshb7splbuei8a.apps.googleusercontent.com";
const OAUTH_CLIENT_SECRET = "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";
const OAUTH_REDIRECT_URI = "http://localhost:3000/oauth2callback";

// OAuth 인증 관리 함수
async function runOAuthAuthentication() {
  // 인증 디렉토리 생성
  if (!fs.existsSync(CONFIG_DIR)) {
    fs.mkdirSync(CONFIG_DIR, { recursive: true });
  }

  // OAuth 클라이언트 생성
  const oauth2Client = new OAuth2Client(OAUTH_CLIENT_ID, OAUTH_CLIENT_SECRET, OAUTH_REDIRECT_URI);

  // OAuth 상세 정보를 키 파일로 저장
  const oauthKeysContent = {
    installed: {
      client_id: OAUTH_CLIENT_ID,
      project_id: "mcp-gmail-connection",
      auth_uri: "https://accounts.google.com/o/oauth2/auth",
      token_uri: "https://oauth2.googleapis.com/token",
      auth_provider_x509_cert_url: "https://www.googleapis.com/oauth2/v1/certs",
      client_secret: OAUTH_CLIENT_SECRET,
      redirect_uris: [OAUTH_REDIRECT_URI],
    },
  };

  // OAuth 키 파일 저장
  fs.writeFileSync(OAUTH_PATH, JSON.stringify(oauthKeysContent, null, 2));
  log(`OAuth keys saved to: ${OAUTH_PATH}`);

  // HTTP 서버 시작
  const server = http.createServer();
  server.listen(3000);
  log("Local server started on port 3000");

  return new Promise((resolve, reject) => {
    // 인증 URL 생성
    const authUrl = oauth2Client.generateAuthUrl({
      access_type: "offline",
      scope: [
        "https://www.googleapis.com/auth/gmail.modify",
        "https://www.googleapis.com/auth/drive.readonly",
        "https://www.googleapis.com/auth/drive",
      ],
    });

    log("Opening browser for authentication...");
    // 브라우저로 인증 페이지 열기
    open(authUrl);

    // 콜백 처리
    server.on("request", async (req, res) => {
      if (!req.url?.startsWith("/oauth2callback")) return;

      const url = new URL(req.url, "http://localhost:3000");
      const code = url.searchParams.get("code");

      if (!code) {
        res.writeHead(400);
        res.end("No code provided");
        reject(new Error("No code provided"));
        return;
      }

      try {
        // 콜백에서 코드를 받아서 토큰 요청
        const { tokens } = await oauth2Client.getToken(code);
        oauth2Client.setCredentials(tokens);

        // 권한 정보 저장
        fs.writeFileSync(CREDENTIALS_PATH, JSON.stringify(tokens, null, 2));
        log(`Credentials saved to: ${CREDENTIALS_PATH}`);

        // 성공 페이지 응답
        res.writeHead(200, { "Content-Type": "text/html" });
        res.end(`
                    <html>
                        <body style="font-family: Arial, sans-serif; text-align: center; padding: 50px;">
                            <h1 style="color: #4285F4;">Authentication Successful!</h1>
                            <p>Google 계정 인증이 완료되었습니다.</p>
                            <p>이 창을 닫고 앱으로 돌아가세요.</p>
                        </body>
                    </html>
                `);

        // 서버 종료 및 성공 반환
        server.close();
        resolve({ success: true, tokens });
      } catch (error) {
        res.writeHead(500);
        res.end("Authentication failed");
        server.close();
        reject(error);
      }
    });

    // 서버 오류 처리
    server.on("error", (error) => {
      log(`Server error: ${error.message}`);
      reject(error);
    });
  });
}
/****************************************************************
 *  MCP-Web-App – 메인 프로세스 진입점
 *
 *  ▸ 이 파일은 Electron ‘메인 프로세스’에서 실행된다.
 *  ▸ 역할
 *      1) Electron 윈도우 생성 및 애플리케이션 생명주기 관리
 *      2) MCP 서버(여기서는 Filesystem 서버) 스폰 & RPC 통신
 *      3) OpenAI LLM 호출 → “어떤 MCP 툴을 쓸지” 의사결정
 *      4) Renderer(브라우저) ↔ Main 간 IPC 브리지
 *
 *  ⚠️  NOTE
 *      ─ Electron 구조
 *          • Main  : Node.js 런타임, OS 자원 접근 가능
 *          • Renderer : Chromium, DOM 렌더링 / 사용자 UI
 *          • Preload  : 둘 사이를 안전하게 중재(contextIsolation)
 *
 *      ─ MCP 서버
 *          • `@modelcontextprotocol/server-filesystem` 바이너리를
 *            자식 프로세스로 띄우고, stdin/stdout을 통해 JSON-RPC 사용
 ****************************************************************/

require("dotenv").config(); // .env 로부터 환경변수 로드
const { app, BrowserWindow, ipcMain, dialog } = require("electron");
const spawn = require("cross-spawn"); // cross-platform child_process
const axios = require("axios"); // OpenAI REST 호출
const portfinder = require("portfinder"); // (지금은 미사용) 여유 포트 찾기
const { v4: uuid } = require("uuid"); // JSON-RPC id 생성용
const { google } = require("googleapis");
const { OAuth2Client } = require("google-auth-library");
const open = require("open").default;
const http = require("http");

/* ───────────── Logger 헬퍼 ───────────── */
const ts = () => new Date().toISOString();
const log = (...a) => console.log(ts(), "[INFO ]", ...a);
const warn = (...a) => console.warn(ts(), "[WARN ]", ...a);
const err = (...a) => console.error(ts(), "[ERROR]", ...a);

/* ───────────── StdioRPCClient 클래스 ─────────────
   MCP 서버와의 JSON-RPC 통신을 캡슐화한다.
   ▸ stdin.write() 로 요청 전송
   ▸ stdout ‘\n’ 단위로 버퍼링하여 응답 파싱
   ▸ id-Promise 매핑을 Map 으로 관리(pending)
────────────────────────────────────────── */
class StdioRPCClient {
  constructor(proc, tag) {
    this.proc = proc; // child_process 인스턴스
    this.tag = tag; // 로그 식별용 라벨
    this.pending = new Map(); // { id → {resolve, reject} }

    /* --- 데이터 수신 핸들러 등록 --- */
    this.buffer = "";
    proc.stdout.on("data", (d) => this.#onData(d));

    /* --- STDERR → 로그로 라우팅 (서버 에러/경고) --- */
    proc.stderr.on("data", (d) =>
      d
        .toString()
        .split(/\r?\n/)
        .forEach((l) => {
          if (!l) return;
          if (l.startsWith("Secure MCP") || l.startsWith("Allowed")) log(`[${this.tag}]`, l); // 정상 안내 메시지
          else err(`[${this.tag}!]`, l); // 실제 오류
        })
    );
    proc.on("exit", (c) => warn(`[${tag}] exited`, c));
  }

  /* stdout 버퍼 처리 – 한 줄(JSON)씩 분해하여 Promise resolve */
  #onData(chunk) {
    this.buffer += chunk.toString();
    let idx;
    while ((idx = this.buffer.indexOf("\n")) >= 0) {
      const line = this.buffer.slice(0, idx).trim();
      this.buffer = this.buffer.slice(idx + 1);
      if (!line) continue;

      try {
        const msg = JSON.parse(line); // {"jsonrpc":"2.0", id, ...}
        const p = this.pending.get(msg.id); // 대기중인 호출 찾기
        if (p) {
          this.pending.delete(msg.id);
          msg.error ? p.reject(msg.error) : p.resolve(msg.result);
        }
      } catch (e) {
        err(`[${this.tag}] broken JSON`, line);
      }
    }
  }

  /* JSON-RPC 메서드 호출 래퍼 (Promise 반환) */
  call(method, params = {}) {
    const id = uuid();
    const payload = { jsonrpc: "2.0", id, method, params };
    return new Promise((resolve, reject) => {
      this.pending.set(id, { resolve, reject });
      this.proc.stdin.write(JSON.stringify(payload) + "\n");
    });
  }
}

/* ───────────── 0. MCP 서버 정의 ─────────────
   여러 서버를 선택적으로 돌릴 수 있도록 배열로 보관
   (Filesystem 서버와 Gmail 서버)
   기존에 만들어져있던 서버를 설치하여 사용할 경우 서버를 설치한 뒤
   SERVER_DEFS에 서버를 추가하면 실행 시 이 배열 내부를 돌면서 필요한 서버의 정보를 취득함.
────────────────────────────────────────── */

// 🍄 decideCall에서 여러 tool_call 파싱
function parseToolCalls(msg) {
  if (Array.isArray(msg.tool_calls)) {
    return msg.tool_calls.map((tc) => ({
      name: tc.function.name,
      arguments: JSON.parse(tc.function.arguments),
    }));
  } else if (msg.function_call) {
    return [
      {
        name: msg.function_call.name,
        arguments: JSON.parse(msg.function_call.arguments),
      },
    ];
  } else {
    return [];
  }
}

// 🍄 tool_calls 순차 실행 + context 넘겨주기
async function executePlan(toolCalls) {
  const context = {
    results: [],
    previousResult: null,
  };

  log("[executePlan] Starting sequential execution:", toolCalls);

  for (const call of toolCalls) {
    const srvId = call.name.split("_")[0];
    const srv = servers.find((s) => s.id === srvId);
    if (!srv) throw new Error(`server ${srvId} not found`);

    // 인자에 context 삽입
    const args = fillArgumentsWithContext(call.arguments, context);

    const payload = { name: call.name.replace(`${srvId}_`, ""), arguments: args };
    log("[RPC] calling", payload);

    // MCP 표준 호출
    let rpcRes;
    try {
      rpcRes = await srv.rpc.call("call_tool", payload);
    } catch (err) {
      if (err.code === -32601) {
        rpcRes = await srv.rpc.call("tools/call", payload);
      } else {
        throw err;
      }
    }

    // 결과 저장
    let rawResult;
    if (Array.isArray(rpcRes?.content)) {
      rawResult = rpcRes.content
        .filter((c) => c.type === "text")
        .map((c) => c.text)
        .join("\n");
    } else {
      rawResult = JSON.stringify(rpcRes);
    }

    context.previousResult = rawResult;
    context.results.push(rawResult);
  }

  return context;
}

// 🍄 arguments 안에 {{previous_result}} 같은 placeholder 자동으로 채워줌
function fillArgumentsWithContext(argumentsObj, context) {
  const filled = {};

  for (const key in argumentsObj) {
    const val = argumentsObj[key];
    if (typeof val === "string" && val.includes("{{previous_result}}")) {
      filled[key] = val.replace("{{previous_result}}", context.previousResult ?? "");
    } else {
      filled[key] = val;
    }
  }

  return filled;
}

// 🍄 독립적인 병렬 작업일 때 사용하는 함수
async function executePlanParallel(toolCalls) {
  log("[executePlanParallel] Starting parallel execution:", toolCalls);

  const results = await Promise.all(
    toolCalls.map(async (call) => {
      const srvId = call.name.split("_")[0];
      const srv = servers.find((s) => s.id === srvId);
      if (!srv) throw new Error(`server ${srvId} not found`);

      const args = call.arguments;
      const payload = { name: call.name.replace(`${srvId}_`, ""), arguments: args };

      let rpcRes;
      try {
        rpcRes = await srv.rpc.call("call_tool", payload);
      } catch (err) {
        if (err.code === -32601) {
          rpcRes = await srv.rpc.call("tools/call", payload);
        } else {
          throw err;
        }
      }

      let rawResult;
      if (Array.isArray(rpcRes?.content)) {
        rawResult = rpcRes.content
          .filter((c) => c.type === "text")
          .map((c) => c.text)
          .join("\n");
      } else {
        rawResult = JSON.stringify(rpcRes);
      }

      return rawResult;
    })
  );

  return results;
}

// 🍄 previous_result를 써야 한다면 순차, 아니면 병렬
function markRequiresPreviousResult(toolCalls) {
  return toolCalls.map((call) => ({
    ...call,
    requiresPreviousResult: Object.values(call.arguments).some(
      (v) => typeof v === "string" && v.includes("{{previous_result}}")
    ),
  }));
}

const SERVER_DEFS = [
  {
    id: "fs", // 툴 alias 접두사
    name: "Filesystem",
    bin:
      process.platform === "win32" // OS 별 실행 파일
        ? "mcp-server-filesystem.cmd"
        : "mcp-server-filesystem",
    allowedDir: process.cwd(), // 루트 디렉터리 기본값
  },
  {
    id: "gmail", // 툴 alias 접두사
    name: "Gmail",
    bin: process.platform === "win32" ? "gmail-mcp.cmd" : "gmail-mcp",
  },
  {
    id: "gdrive", // ➡️ 추가
    name: "GDrive",
    bin: process.platform === "win32" ? "ej-mcp-server-gdrive.cmd" : "ej-mcp-server-gdrive",
  },
];

/* ───────────── 1. 런타임 상태 ───────────── */
const servers = []; // [{ id, name, proc, rpc, tools[], allowedDir }]

/* ───────────── 2. 서버 스폰 & 툴 로딩 ───────────── */
async function spawnServer(def) {
  const binPath = path.join(__dirname, "node_modules", ".bin", def.bin);
  if (!fs.existsSync(binPath)) {
    err("not found", binPath);
    return null;
  }

  log(`Spawning ${def.id}`, binPath, def.allowedDir);
  /* child_process.spawn
     stdio = [stdin, stdout, stderr] 모두 파이프로 연결 */
  const proc = spawn(binPath, [def.allowedDir], {
    cwd: def.allowedDir,
    stdio: ["pipe", "pipe", "pipe"],
  });

  const rpc = new StdioRPCClient(proc, def.id);
  const srv = { ...def, proc, rpc, tools: [] };

  await refreshTools(srv); // list_tools → API 스키마 획득
  servers.push(srv);

  /* aliasMap 은 툴 호출 이름 → {srvId, method} 매핑 */
  aliasMap.clear(); // 서버 재시작 시 새로 갱신
  return srv;
}

/* 서버에서 지원하는 툴 목록 가져와서 (서버별) 저장 */
async function refreshTools(srv) {
  try {
    // 서버 버전에 따라 list_tools 또는 tools/list 지원
    let raw;
    try {
      log("start list_tool");
      raw = await srv.rpc.call("list_tools");
      log("end list_tool");
    } catch {
      log("start tools/list");
      raw = await srv.rpc.call("tools/list");
      log("end tools/list");
    }

    // 다양한 응답 형식을 배열로 정규화
    let arr = [];
    if (Array.isArray(raw)) arr = raw;
    else if (raw?.tools) arr = raw.tools;
    else if (typeof raw === "object") arr = Object.values(raw);

    if (!arr.length) throw new Error("no tools found");

    /* name 충돌 방지를 위해 “srvid_toolname” 으로 alias 부여 */
    srv.tools = arr.map((t) => ({
      ...t,
      name: `${srv.id}_${t.name}`,
      _origMethod: t.name, // 실제 서버 측 메서드 기억
    }));

    log(
      `Tools[${srv.id}] loaded`,
      srv.tools.map((t) => t.name)
    );
  } catch (e) {
    err("tool load failed", e.message);
  }
}

/* 모든 서버의 툴 평탄화(Prompts에서 tools 필드로 넘김) */
function allTools() {
  return servers.flatMap((s) => s.tools);
}

// 🍄 타입 틀린 tools 빼고 전송
function allToolsForLLM() {
  return servers.flatMap((s) =>
    s.tools.filter((t) => {
      // 1) inputSchema가 object 타입이고
      const input = t.inputSchema || t.parameters;
      if (!input || input.type !== "object") return false;

      // 2) properties 정의가 정상적이고
      if (!input.properties || typeof input.properties !== "object") return false;

      // 3) additionalProperties 없거나 true일 때만 허용
      if (input.additionalProperties === false) return false;

      return true;
    })
  );
}

/* OpenAI ChatGPT v2 “function calling” 스펙용 변환 🍄 수정*/
function formatToolV2(t) {
  aliasMap.set(t.name, {
    srvId: t.name.split("_", 1)[0],
    method: t._origMethod,
  });

  return {
    type: "function",
    function: {
      name: t.name,
      description: t.description || "No description provided",
      parameters: {
        type: "object",
        properties: t.inputSchema?.properties || t.parameters?.properties || {},
        required: t.inputSchema?.required || t.parameters?.required || [],
      },
    },
  };
}

const aliasMap = new Map(); // {alias → {srvId, method}}

/* ─────────── 3. OpenAI → 어떤 툴 쓸지 결정 또는 직접 응답 ─────────────
   ① 유저 프롬프트, ② 서버 툴 스키마 → Chat Completions 호출
   ▸ LLM 결과가 "tool_call" 이면 RPC 실행, 아니면 텍스트 그대로 응답
────────────────────────────────────────── */
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
You are a helpful assistant capable of chaining multiple tool actions.

Guidelines:
1. STEP PLANNING
   • If the user's request requires multiple steps (such as read-then-send), break it down into an ordered list of actions.
   • Each action must specify a tool name and required arguments.
   • If later steps need earlier results (e.g., sending a read file), insert "{{previous_result}}" where the output should go.

2. TOOL CALL
  • Use only provided tool names and their schemas.
   • Tool names are prefixed by their service (e.g., "gdrive_read_file_content", "gmail_send_email").
   • If a request requires filesystem access (reading, writing, listing, etc.), emit exactly one tool call JSON with the correct tool name and all required parameters.
   • Use only the provided tool names and schemas—do not invent new tools or free-form code.
   • If the user did not specify a path (or uses "/" or "."), use the current project root directory instead.
   • When accessing files in Google Drive, users do not need to provide file IDs. File names (e.g., "test.txt" or "test") are sufficient, and the server will automatically search for and find the file. Do not ask for file IDs.
   • When accessing files in Google Drive:
       - Users do not need to provide file IDs. File names (e.g., "test.txt" or "test") are sufficient, and the server will automatically search for and find the file. Do not ask for file IDs.
       - To replace the entire file content, use "update_file_content".
       - To append new text to an existing file, use "append_file_content".
       - To delete specific text from a file, use "delete_from_file_content".
       - To simply read or view a file's content, use "read_file_content".
       - Always select the tool that most precisely matches the user's intention.
3. TEXT RESPONSE
   • For general questions, conversations, or requests that don't need filesystem access, just respond normally with helpful information.
   • Always respond in Korean unless specifically asked for another language.
3-1. OUTPUT FORMAT
   • Always respond with a list of tool_calls, NOT natural language explanations.
   • Each tool call includes:
     - function name
     - JSON stringified arguments
3-2. PLACEHOLDER
   • To reuse the previous step's result, insert "{{previous_result}}" in the argument field.
4. FOLLOW-UP QUESTIONS
   • If a required parameter is missing or ambiguous, ask the user a clarifying question instead of guessing.
5. EXAMPLES
Request: "Send 'test.txt' in Google Drive to whdsmdl401@naver.com"
Plan:
[
  {
    "name": "gdrive_read_file_content",
    "arguments": { "filename": "test.txt" }
  },
  {
    "name": "gmail_send_email",
    "arguments": {
      "to": "whdsmdl401@naver.com",
      "subject": "Requested File",
      "body": "{{previous_result}}"
    }
  }
]

⚠ Always output only the JSON list of tool_calls.

`,
        },
        { role: "user", content: prompt },
      ],
      tools: allToolsForLLM().map(formatToolV2),
      tool_choice: "auto",
      max_tokens: 1024,
    },
    { headers: { Authorization: `Bearer ${key}` } }
  );

  log("[LLM] raw response:", JSON.stringify(res.data, null, 2));
  const msg = res.data.choices[0].message;

  // multiple tool_calls 가능하게
  const toolCalls = markRequiresPreviousResult(parseToolCalls(msg));
  log("[Plan] toolCalls:", toolCalls);

  if (toolCalls.length === 0 && msg.content) {
    try {
      const fallbackParsed = JSON.parse(msg.content);
      if (Array.isArray(fallbackParsed)) {
        log("[Fallback] parsed toolCalls from content:", fallbackParsed);
        return {
          type: "toolCalls",
          toolCalls: markRequiresPreviousResult(fallbackParsed),
        };
      }
    } catch (e) {
      log("[Fallback] content parsing failed:", e.message);
    }
  }

  if (toolCalls.length === 0) {
    // 툴 호출이 없으면 일반 텍스트 응답
    return { type: "text", content: msg.content ?? "" };
  }

  // /* ─ OpenAI 2024 이후 포맷: message.tool_calls[] ─ */
  // let fc = null;
  // if (Array.isArray(msg.tool_calls) && msg.tool_calls.length) fc = msg.tool_calls[0].function;
  // /* ─ 레거시(v1) 포맷: function_call ─ */ else if (msg.function_call) fc = msg.function_call;

  // // 툴 호출이 없으면 텍스트 응답 (일반 질문으로 처리)
  // if (!fc || !fc.arguments) return { type: "text", content: msg.content ?? "" };

  // 툴 인자 JSON 파싱
  // let parsed;
  // try {
  //   parsed = JSON.parse(fc.arguments);
  // } catch {
  //   err("Failed to parse tool arguments:", fc.arguments);
  //   return { type: "text", content: msg.content ?? "" };
  // }

  // const alias = fc.name; // e.g. fs_directory_tree
  // const params = parsed.params || parsed; // (서버 마다 다름)

  // /* ───── 경로 보정 ─────
  //   LLM이 '/'·'.'·'' 같이 루트 의미로 응답하면
  //   MCP 서버 쪽엔 '.'(allowedDir)로 넘겨서
  //   "허용된 디렉터리 바깥" 오류를 방지 */
  // if (typeof params.path === "string") {
  //   const p = params.path.trim();
  //   if (p === "/" || p === "\\" || p === "." || p === "") {
  //     params.path = "."; // Filesystem 서버는 '.'을 프로젝트 루트로 해석
  //   }
  // }

  // const map = aliasMap.get(alias);
  // if (!map) {
  //   err("Unmapped tool alias:", alias);
  //   return { type: "text", content: msg.content ?? "" };
  // }

  return {
    type: "toolCalls",
    toolCalls,
  };
}

/* ───────────── 4. Electron 윈도우 생성 ───────────── */
let mainWindow;
function createWindow() {
  log("createWindow");
  mainWindow = new BrowserWindow({
    width: 1000,
    height: 700,
    webPreferences: {
      preload: path.join(__dirname, "preload.js"), // contextBridge 코드
      contextIsolation: true, // Renderer → Main 완전 격리
    },
  });
  mainWindow.loadFile(path.join(__dirname, "renderer", "index.html"));

  // 개발자 도구 콘솔 오픈
  mainWindow.webContents.openDevTools();
}

/* ───────────── 5. IPC 라우팅 ─────────────
   Renderer → Main
     'select-folder' : 폴더 선택 다이얼로그 열기
     'run-command'   : 사용자 자연어 명령 처리
     'google-auth'   : Google OAuth 인증 수행
────────────────────────────────────────── */
ipcMain.handle("select-folder", async () => {
  // ① OS 폴더 선택 UI
  const r = await dialog.showOpenDialog({ properties: ["openDirectory"] });
  if (r.canceled) return null;

  const dir = r.filePaths[0];
  log("folder selected", dir);

  /* ② 기존 fs 서버 종료 → 새 allowedDir 로 재시작 */
  const idx = servers.findIndex((s) => s.id === "fs");
  if (idx >= 0) {
    servers[idx].proc.kill();
    servers.splice(idx, 1);
  }
  await spawnServer({ ...SERVER_DEFS[0], allowedDir: dir });
  return dir;
});

// Google 인증 처리를 위한 새 IPC 핸들러
ipcMain.handle("google-auth", async () => {
  log("[IPC] google-auth 시작");
  try {
    const gmailServerDef = SERVER_DEFS.find((s) => s.id === "gmail");
    const gdriveServerDef = SERVER_DEFS.find((s) => s.id === "gdrive"); // ⭐ 추가

    // 이미 실행 중이면 종료
    const gmailServerIdx = servers.findIndex((s) => s.id === "gmail");
    if (gmailServerIdx >= 0) {
      log(`기존 Gmail 서버 종료`);
      servers[gmailServerIdx].proc.kill();
      servers.splice(gmailServerIdx, 1);
    }

    const gdriveServerIdx = servers.findIndex((s) => s.id === "gdrive");
    if (gdriveServerIdx >= 0) {
      log(`기존 GDrive 서버 종료`);
      servers[gdriveServerIdx].proc.kill();
      servers.splice(gdriveServerIdx, 1);
    }

    // 직접 OAuth 인증 시도 (기본 제공되는 키 사용)
    try {
      log("[OAuth] 직접 인증 시도 시작");
      const authResult = await runOAuthAuthentication();

      if (authResult.success) {
        // Gmail 서버 실행
        log(`인증 성공, Gmail 서버 스폰 시도`);
        const gmailServer = await spawnServer(gmailServerDef);
        if (!gmailServer) throw new Error("Gmail 서버 시작 실패");

        // GDrive 서버 실행 ⭐ 추가
        log(`인증 성공, GDrive 서버 스폰 시도`);
        const gdriveServer = await spawnServer(gdriveServerDef);
        if (!gdriveServer) throw new Error("GDrive 서버 시작 실패");

        return {
          success: true,
          message: "Google 계정 인증이 완료되었습니다. 이제 Gmail과 GDrive 기능을 사용할 수 있습니다.",
        };
      }
    } catch (oauthError) {
      log(`[OAuth] 직접 인증 실패: ${oauthError.message}`);
      throw oauthError; // 에러 전파
    }
  } catch (e) {
    err("Google auth failed", e);
    return {
      success: false,
      message: `Google 계정 인증 중 오류 발생: ${e.message}`,
      error: e.message,
    };
  }
});

ipcMain.handle("run-command", async (_e, prompt) => {
  log("[IPC] run-command", prompt);
  try {
    // 1. LLM에 Plan 요청
    const d = await decideCall(prompt);

    // 일반 질문인 경우 - 텍스트 응답을 바로 반환
    if (d.type === "text") return { result: d.content };

    // 2. toolCalls 추출출
    const toolCalls = d.toolCalls; // ➡️ decideCall에서 배열로 반환해야 함

    if (!Array.isArray(toolCalls) || toolCalls.length === 0) {
      throw new Error("도구 호출이 없습니다. Plan 생성 실패");
    }

    /** 3. Plan 실행 (순차 or 병렬) */
    let context;

    if (toolCalls.some((call) => call.requiresPreviousResult)) {
      // 연쇄 의존 관계가 필요한 경우
      context = await executePlan(toolCalls);
    } else {
      // 독립적인 작업은 병렬 실행
      const results = await executePlanParallel(toolCalls);
      context = { results, previousResult: results.at(-1) }; // 마지막 결과
    }

    // 4. 결과 요약
    const rawSummary = context.results.map((r, i) => `Step ${i + 1}: ${r}`).join("\n\n");

    // MCP 도구 호출이 필요한 경우 - 기존 코드
    /* ② RPC 실행 대상 서버 탐색 */
    // const srv = servers.find((s) => s.id === d.srvId);
    // if (!srv) throw new Error(`server ${d.srvId} not found`);

    // const payload = { name: d.method, arguments: d.params };
    // log("[RPC] calling call_tool", payload);

    // /* ③ MCP 표준: call_tool 또는 tools/call */
    // let rpcRes;
    // try {
    //   rpcRes = await srv.rpc.call("call_tool", payload);
    // } catch (err) {
    //   if (err.code === -32601) {
    //     log("[RPC] call_tool not found, falling back to tools/call");
    //     rpcRes = await srv.rpc.call("tools/call", payload);
    //   } else {
    //     throw err;
    //   }
    // }

    // /* ④ MCP 서버의 응답 : content 배열 중 text 항목 추출 */
    // let rawResult;
    // if (Array.isArray(rpcRes?.content)) {
    //   rawResult = rpcRes.content
    //     .filter((c) => c.type === "text")
    //     .map((c) => c.text)
    //     .join("\n");
    // } else {
    //   rawResult = JSON.stringify(rpcRes);
    // }
    // log("[RPC] rawResult:", rawResult);

    /* ⑤ 결과를 한글 자연어로 요약(2차 OpenAI 호출) */
    const postRes = await axios.post(
      "https://api.openai.com/v1/chat/completions",
      {
        model: "gpt-4o-mini",
        messages: [
          {
            role: "system",
            content:
              "You are a helpful assistant. The user performed multiple tool actions.\n" +
              "Summarize the steps and results briefly and clearly, in natural Korean.\n",
          },
          { role: "user", content: `Original request:\n${prompt}` },
          { role: "assistant", content: `Tool outputs:\n${rawSummary}` },
        ],
      },
      { headers: { Authorization: `Bearer ${process.env.OPENAI_API_KEY}` } }
    );

    const finalAnswer = postRes.data.choices[0].message.content.trim();
    log("[POST-PROCESS] final answer:", finalAnswer);
    return { result: finalAnswer };
  } catch (e) {
    err("cmd fail", e);
    return { error: e.message };
  }
});

/* ───────────── 6. Electron App 생명주기 ───────────── */
app.whenReady().then(async () => {
  log("Electron ready");
  // Filesystem 서버만 시작 (Gmail은 인증 버튼 클릭 시 시작)
  await spawnServer(SERVER_DEFS.find((s) => s.id === "fs"));
  createWindow();
});
app.on("will-quit", () => servers.forEach((s) => s.proc.kill()));
