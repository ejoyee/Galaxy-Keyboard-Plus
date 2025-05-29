import express from "express";
import { spawn } from "child_process";
import bodyParser from "body-parser";

const app = express();
app.use(bodyParser.json());
const port = 8160;

let childProcess;
let isShuttingDown = false;

function startMCPProcess() {
  childProcess = spawn("/usr/bin/env", ["python3", "-m", "opencv_mcp_server.main"], {
    cwd: "/app", 
    env: {
      ...process.env,
      PYTHONPATH: "/app", 
    },
  });

  childProcess.stdout.on("data", (data) => {
    console.log(`OpenCV MCP Output: ${data}`);
  });

  childProcess.stderr.on("data", (data) => {
    console.error(`OpenCV MCP Error: ${data}`);
  });

  childProcess.on("close", (code) => {
    console.log(`OpenCV MCP 종료 (코드: ${code})`);
    if (code !== 0 && !isShuttingDown) {
      console.log("비정상 종료, 5초 후 재시작...");
      setTimeout(startMCPProcess, 5000);
    }
  });

  childProcess.on("error", (err) => {
    console.error("OpenCV MCP 프로세스 오류:", err);
  });

  return childProcess;
}

childProcess = startMCPProcess();

// 종료 처리
process.on("SIGINT", () => {
  isShuttingDown = true;
  childProcess.kill();
  process.exit(0);
});

// JSON-RPC 처리
app.post("/", async (req, res) => {
  try {
    const request = req.body;
    if (!request || !request.id) {
      throw new Error("잘못된 JSON-RPC 요청 (id 없음)");
    }
    console.log("[OpenCV MCP] 요청 수신:", JSON.stringify(request));

    const mcpRequest = request; // 변환 없음

    childProcess.stdin.write(JSON.stringify(mcpRequest) + "\n");

    const responsePromise = new Promise((resolve, reject) => {
      const requestId = mcpRequest.id;
      const timeout = setTimeout(() => {
        removeHandler();
        reject(new Error("요청 시간 초과"));
      }, 30000);

      let buffer = "";

      const handler = (data) => {
        buffer += data.toString();
        try {
          const response = JSON.parse(buffer);
          if (response.id === requestId) {
            clearTimeout(timeout);
            removeHandler();
            resolve(response);
          }
        } catch (e) {
          // 아직 완전한 JSON이 아님
        }
      };

      const removeHandler = () => {
        childProcess.stdout.removeListener("data", handler);
      };

      childProcess.stdout.on("data", handler);
    });

    const response = await responsePromise;
    res.json(response);
  } catch (err) {
    console.error("오류:", err);
    res.status(500).json({
      jsonrpc: "2.0",
      id: req.body.id || null,
      error: {
        code: -32000,
        message: `내부 서버 오류: ${err.message}`,
      },
    });
  }
});

app.get("/health", (req, res) => {
  res.status(200).json({ status: "OK" });
});

app.listen(port, () => {
  console.log(`OpenCV MCP Proxy 서버가 ${port}번 포트에서 실행 중`);
});
