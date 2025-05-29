import express from "express";
import { spawn } from "child_process";
import bodyParser from "body-parser";

const app = express();
app.use(bodyParser.json());
const port = 8180;

let childProcess;
let isShuttingDown = false;

function startMCPProcess() {
  childProcess = spawn(
    "npx",
    ["-y", "@openbnb/mcp-server-airbnb"],
    {
      cwd: "/app",
      env: {
        ...process.env,
      },
    }
  );

  childProcess.stdout.on("data", (data) => {
    console.log(`Airbnb MCP Output: ${data}`);
  });

  childProcess.stderr.on("data", (data) => {
    console.log(`Airbnb MCP Log: ${data}`);
  });

  childProcess.on("close", (code) => {
    console.log(`Airbnb MCP 프로세스 종료 (코드: ${code})`);
    if (code !== 0 && !isShuttingDown) {
      console.log("[Airbnb MCP] 비정상 종료, 5초 후 재시작...");
      setTimeout(startMCPProcess, 5000);
    }
  });

  childProcess.on("error", (err) => {
    console.error("Airbnb MCP 오류:", err);
  });

  return childProcess;
}

childProcess = startMCPProcess();

process.on("SIGINT", () => {
  isShuttingDown = true;
  childProcess.kill();
  process.exit(0);
});

app.post("/", async (req, res) => {
  try {
    const request = req.body;
    console.log("[Airbnb MCP] Received HTTP request:", JSON.stringify(request));

    let mcpRequest;
    if (request.method === "call_tool") {
      mcpRequest = {
        jsonrpc: "2.0",
        id: request.id,
        method: "tools/call",
        params: request.params,
      };
    } else if (request.method === "list_tools") {
      mcpRequest = {
        jsonrpc: "2.0",
        id: request.id,
        method: "tools/list",
        params: request.params || {},
      };
    } else {
      mcpRequest = request;
    }

    console.log("[Airbnb MCP] Transformed request:", JSON.stringify(mcpRequest));

    childProcess.stdin.write(JSON.stringify(mcpRequest) + "\n");

    const responsePromise = new Promise((resolve, reject) => {
      const requestId = mcpRequest.id;
      const timeout = setTimeout(() => {
        console.error("MCP 요청 시간 초과");
        removeResponseHandler();
        reject(new Error("Request timed out"));
      }, 30000);

      let responseBuffer = "";

      const responseHandler = (data) => {
        responseBuffer += data.toString();
        try {
          let response;
          let validJsonFound = false;

          try {
            response = JSON.parse(responseBuffer);
            validJsonFound = true;
          } catch {}

          if (validJsonFound && response.id === requestId) {
            clearTimeout(timeout);
            removeResponseHandler();
            console.log("[Airbnb MCP] Received MCP response:", JSON.stringify(response));
            resolve(response);
          } else if (validJsonFound) {
            console.log("[Airbnb MCP] 다른 요청 응답 수신, 대기 중...");
            responseBuffer = "";
          }
        } catch (e) {
          console.error("[Airbnb MCP] 응답 파싱 오류:", e);
        }
      };

      const removeResponseHandler = () => {
        childProcess.stdout.removeListener("data", responseHandler);
      };

      childProcess.stdout.on("data", responseHandler);
    });

    const response = await responsePromise;
    res.json(response);
  } catch (error) {
    console.error("[Airbnb MCP] 처리 오류:", error);
    res.status(500).json({
      jsonrpc: "2.0",
      id: req.body.id || null,
      error: {
        code: -32000,
        message: `[Airbnb MCP] 내부 서버 오류: ${error.message}`,
      },
    });
  }
});

app.get("/health", (req, res) => {
  res.status(200).send("OK");
});

console.log("Airbnb MCP Proxy Starting...");

app.listen(port, () => {
  console.log(`Airbnb HTTP Proxy running on port ${port}`);
});
