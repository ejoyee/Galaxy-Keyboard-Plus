import express from "express";
import { spawn } from "child_process";
import bodyParser from "body-parser";

const app = express();
const port = 8170;
app.use(bodyParser.json());

// Google Maps MCP 프로세스 관리
let childProcess;
let isShuttingDown = false;

function startMCPProcess() {
  childProcess = spawn(
    "npx",
    ["-y", "@modelcontextprotocol/server-google-maps"], // ← Brave → Google Maps
    {
      cwd: "/app",
      env: {
        ...process.env,
        GOOGLE_MAPS_API_KEY: process.env.GOOGLE_MAPS_API_KEY, // ← 키 이름 변경
      },
    }
  );

  childProcess.stdout.on("data", d => console.log(`Google MCP ▶ ${d}`));
  childProcess.stderr.on("data", d => console.log(`Google MCP ⚠ ${d}`));

  childProcess.on("close", code => {
    console.log(`Google MCP 종료 (code=${code})`);
    if (code !== 0 && !isShuttingDown) {
      console.log("비정상 종료, 5초 후 재시도…");
      setTimeout(startMCPProcess, 5000);
    }
  });

  childProcess.on("error", err => console.error("Google MCP 오류:", err));
}

startMCPProcess();

// 종료 신호 처리
process.on("SIGINT", () => {
  isShuttingDown = true;
  childProcess.kill();
  process.exit(0);
});

// JSON-RPC 프록시
app.post("/", async (req, res) => {
  const original = req.body;
  try {
    // 메서드명 변환
    const mcpRequest =
      original.method === "call_tool"
        ? { jsonrpc: "2.0", id: original.id, method: "tools/call", params: original.params }
        : original.method === "list_tools"
          ? { jsonrpc: "2.0", id: original.id, method: "tools/list", params: original.params || {} }
          : original;

    // 요청 전송
    childProcess.stdin.write(JSON.stringify(mcpRequest) + "\n");

    // 동일 id 응답만 전달
    const response = await new Promise((resolve, reject) => {
      let buf = "";
      const timer = setTimeout(() => reject(new Error("timeout")), 30000);

      const handler = chunk => {
        buf += chunk.toString();
        try {
          const json = JSON.parse(buf);
          if (json.id === mcpRequest.id) {
            clearTimeout(timer);
            childProcess.stdout.off("data", handler);
            resolve(json);
          }
        } catch { /* incomplete JSON → keep buffering */ }
      };
      childProcess.stdout.on("data", handler);
    });

    res.json(response);
  } catch (e) {
    console.error("프록시 오류:", e);
    res.status(500).json({
      jsonrpc: "2.0",
      id: original.id ?? null,
      error: { code: -32000, message: e.message },
    });
  }
});

// 헬스 체크
app.get("/health", (_, res) => res.status(200).send("OK"));

console.log(
  `GOOGLE_MAPS_API_KEY is ${process.env.GOOGLE_MAPS_API_KEY ? "set" : "NOT set"}`
);
app.listen(port, () => console.log(`Google Maps HTTP proxy on :${port}`));
