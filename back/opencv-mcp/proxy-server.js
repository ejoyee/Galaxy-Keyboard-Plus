import express from "express";
import { spawn } from "child_process";
import bodyParser from "body-parser";

const app = express();
app.use(bodyParser.json());
const port = 8160;

let childProcess;
let isShuttingDown = false;
let mcpReady = false;
let mcpInitialized = false;
let outputBuffer = "";
const pendingRequests = new Map();
let debugLogs = [];

// 디버그 로그 함수
function debugLog(message, data = null) {
  const timestamp = new Date().toISOString();
  const logEntry = { timestamp, message, data };
  debugLogs.push(logEntry);
  
  if (debugLogs.length > 100) {
    debugLogs = debugLogs.slice(-100);
  }
  
  console.log(`[DEBUG ${timestamp}] ${message}`, data ? JSON.stringify(data) : '');
}

function startMCPProcess() {
  debugLog("MCP 프로세스 시작 시도");
  
  childProcess = spawn("/usr/bin/env", ["python3", "-m", "opencv_mcp_server.main"], {
    cwd: "/app", 
    stdio: ['pipe', 'pipe', 'pipe'],
    env: {
      ...process.env,
      PYTHONPATH: "/app",
      PYTHONUNBUFFERED: "1",
      MCP_TRANSPORT: "stdio"
    },
  });

  debugLog("MCP 프로세스 생성됨", { pid: childProcess.pid });

  // stdout 처리
  childProcess.stdout.on("data", (data) => {
    const rawData = data.toString();
    debugLog("Raw stdout 데이터 수신", { content: rawData });
    
    outputBuffer += rawData;
    
    // 줄바꿈으로 구분된 JSON 메시지들 처리
    const lines = outputBuffer.split('\n');
    outputBuffer = lines.pop() || '';
    
    lines.forEach((line, index) => {
      const trimmed = line.trim();
      if (trimmed) {
        debugLog(`줄 ${index} 처리`, { line: trimmed });
        
        try {
          const response = JSON.parse(trimmed);
          debugLog("JSON 파싱 성공", response);
          console.log(`[MCP 응답] ${JSON.stringify(response)}`);
          
          // 대기 중인 요청에 응답 전달
          if (response.id && pendingRequests.has(response.id)) {
            const { resolve, timeout } = pendingRequests.get(response.id);
            clearTimeout(timeout);
            pendingRequests.delete(response.id);
            debugLog("요청-응답 매칭 성공", { requestId: response.id });
            resolve(response);
          } else {
            debugLog("요청-응답 매칭 실패", { 
              responseId: response.id, 
              pendingIds: Array.from(pendingRequests.keys()) 
            });
          }
        } catch (e) {
          debugLog("JSON 파싱 실패", { line: trimmed, error: e.message });
          console.log(`[MCP 비JSON 출력] ${trimmed}`);
        }
      }
    });
  });

  // stderr 처리
  childProcess.stderr.on("data", (data) => {
    const output = data.toString();
    debugLog("stderr 데이터", { content: output });
    console.log(`[MCP 로그] ${output.trim()}`);
    
    // MCP 서버 준비 상태 확인
    if (output.includes("All tools registered successfully")) {
      mcpReady = true;
      debugLog("MCP 서버 준비 완료 감지");
      console.log("✅ MCP 서버 준비 완료");
      
      // 초기화 시작
      setTimeout(() => initializeMCP(), 1000);
    }
    
    if (output.includes("Starting OpenCV MCP server")) {
      debugLog("MCP 서버 시작 감지");
      console.log("🚀 MCP 서버 시작됨");
    }
  });

  childProcess.on("close", (code) => {
    debugLog("MCP 프로세스 종료", { code: code });
    console.log(`MCP 프로세스 종료 (코드: ${code})`);
    mcpReady = false;
    mcpInitialized = false;
    
    const pendingCount = pendingRequests.size;
    pendingRequests.forEach(({ reject, timeout }, id) => {
      clearTimeout(timeout);
      reject(new Error("MCP 프로세스 종료됨"));
    });
    pendingRequests.clear();
    
    debugLog("대기 중인 요청들 정리 완료", { clearedCount: pendingCount });
    
    if (code !== 0 && !isShuttingDown) {
      console.log("❌ 비정상 종료, 5초 후 재시작...");
      debugLog("프로세스 재시작 예약");
      setTimeout(startMCPProcess, 5000);
    }
  });

  childProcess.on("error", (err) => {
    debugLog("MCP 프로세스 오류", { error: err.message });
    console.error("❌ MCP 프로세스 오류:", err);
    mcpReady = false;
    mcpInitialized = false;
  });

  return childProcess;
}

// MCP 알림 전송 함수 (응답 없음)
function sendMCPNotification(notification) {
  debugLog("MCP 알림 전송", { notification: notification });
  
  if (!childProcess || childProcess.killed) {
    debugLog("MCP 알림 실패 - 프로세스 없음");
    return;
  }
  
  try {
    const notificationStr = JSON.stringify(notification) + '\n';
    debugLog("알림 전송 시도", { notificationString: notificationStr });
    
    console.log(`[MCP 알림] ${JSON.stringify(notification)}`);
    childProcess.stdin.write(notificationStr);
    
    debugLog("알림 전송 완료");
    
  } catch (error) {
    debugLog("알림 전송 실패", { error: error.message });
  }
}

// MCP 초기화 프로토콜
async function initializeMCP() {
  debugLog("MCP 초기화 시작");
  
  try {
    console.log("🔄 MCP 초기화 중...");
    
    // 1단계: initialize 요청
    debugLog("1단계: initialize 요청 전송");
    const initResponse = await sendMCPRequest({
      jsonrpc: "2.0",
      id: "initialize-1",
      method: "initialize",
      params: {
        protocolVersion: "2024-11-05",
        capabilities: {
          roots: {
            listChanged: false
          },
          sampling: {}
        },
        clientInfo: {
          name: "opencv-mcp-proxy",
          version: "1.0.0"
        }
      }
    }, 10000);
    
    debugLog("initialize 응답 수신", initResponse);
    
    if (initResponse.error) {
      throw new Error(`초기화 실패: ${initResponse.error.message}`);
    }
    
    // 2단계: initialized 알림 (응답 없는 notification)
    debugLog("2단계: initialized 알림 전송");
    sendMCPNotification({
      jsonrpc: "2.0",
      method: "notifications/initialized",
      params: {}
    });
    
    // 알림 후 잠시 대기
    await new Promise(resolve => setTimeout(resolve, 1000));
    
    mcpInitialized = true;
    debugLog("MCP 초기화 완료");
    console.log("✅ MCP 초기화 완료");
    
    // 3단계: 연결 테스트
    setTimeout(() => testMCPConnection(), 1000);
    
  } catch (error) {
    debugLog("MCP 초기화 실패", { error: error.message });
    console.error("❌ MCP 초기화 실패:", error.message);
    mcpInitialized = false;
  }
}

// MCP 연결 테스트
async function testMCPConnection() {
  debugLog("MCP 연결 테스트 시작");
  
  try {
    console.log("🔍 MCP 연결 테스트 중...");
    debugLog("현재 상태", {
      mcpReady: mcpReady,
      mcpInitialized: mcpInitialized,
      processRunning: childProcess && !childProcess.killed,
      pendingRequestsCount: pendingRequests.size
    });
    
    if (!mcpInitialized) {
      throw new Error("MCP가 아직 초기화되지 않음");
    }
    
    const response = await sendMCPRequest({
      jsonrpc: "2.0",
      id: "connection-test",
      method: "tools/list",
      params: {}
    }, 10000);
    
    debugLog("연결 테스트 응답 수신", response);
    
    if (response.error) {
      throw new Error(`도구 목록 요청 실패: ${response.error.message}`);
    }
    
    const toolCount = response.result?.tools?.length || 0;
    console.log(`✅ 연결 테스트 성공: ${toolCount}개 도구 발견`);
    debugLog("연결 테스트 성공", { toolCount: toolCount });
    
  } catch (error) {
    debugLog("연결 테스트 실패", { error: error.message });
    console.error("❌ 연결 테스트 실패:", error.message);
  }
}

// MCP 요청 전송 함수
function sendMCPRequest(request, timeoutMs = 30000) {
  return new Promise((resolve, reject) => {
    debugLog("MCP 요청 시작", { request: request, timeout: timeoutMs });
    
    if (!childProcess || childProcess.killed) {
      const error = new Error("MCP 프로세스가 실행되지 않음");
      debugLog("MCP 요청 실패 - 프로세스 없음");
      reject(error);
      return;
    }
    
    // initialize는 mcpReady만 확인
    const isInitRequest = request.method === "initialize";
    
    if (!isInitRequest && (!mcpReady || !mcpInitialized)) {
      const error = new Error("MCP 서버가 아직 준비되지 않음");
      debugLog("MCP 요청 실패 - 서버 미준비", { mcpReady, mcpInitialized });
      reject(error);
      return;
    }
    
    const requestId = request.id;
    debugLog("요청 ID 생성", { requestId: requestId });
    
    // 타임아웃 설정
    const timeout = setTimeout(() => {
      if (pendingRequests.has(requestId)) {
        pendingRequests.delete(requestId);
        const error = new Error(`요청 시간 초과 (${timeoutMs}ms)`);
        debugLog("요청 시간 초과", { requestId: requestId, timeout: timeoutMs });
        reject(error);
      }
    }, timeoutMs);
    
    // 요청 저장
    pendingRequests.set(requestId, { resolve, reject, timeout });
    debugLog("요청 등록 완료", { 
      requestId: requestId, 
      totalPending: pendingRequests.size
    });
    
    // 요청 전송
    try {
      const requestStr = JSON.stringify(request) + '\n';
      debugLog("요청 전송 시도", { requestString: requestStr });
      
      console.log(`[MCP 요청] ${JSON.stringify(request)}`);
      childProcess.stdin.write(requestStr);
      
      debugLog("요청 전송 완료", { requestId: requestId });
      
    } catch (error) {
      clearTimeout(timeout);
      pendingRequests.delete(requestId);
      debugLog("요청 전송 실패", { requestId: requestId, error: error.message });
      reject(error);
    }
  });
}

// API 엔드포인트들
app.get("/health", (req, res) => {
  res.status(200).json({ 
    status: "OK",
    mcpReady: mcpReady,
    mcpInitialized: mcpInitialized,
    processRunning: childProcess && !childProcess.killed,
    pendingRequests: pendingRequests.size,
    pid: childProcess?.pid
  });
});

app.get("/debug", (req, res) => {
  res.json({
    mcpReady: mcpReady,
    mcpInitialized: mcpInitialized,
    processRunning: childProcess && !childProcess.killed,
    pid: childProcess?.pid,
    pendingRequests: pendingRequests.size,
    pendingRequestIds: Array.from(pendingRequests.keys()),
    outputBuffer: outputBuffer,
    outputBufferLength: outputBuffer.length,
    recentLogs: debugLogs.slice(-20),
    processInfo: childProcess ? {
      killed: childProcess.killed,
      exitCode: childProcess.exitCode,
      signalCode: childProcess.signalCode
    } : null
  });
});

// 수동 초기화 엔드포인트
app.post("/initialize", async (req, res) => {
  try {
    debugLog("수동 초기화 API 호출");
    await initializeMCP();
    res.json({ success: true, message: "초기화 완료" });
  } catch (error) {
    debugLog("수동 초기화 실패", { error: error.message });
    res.status(500).json({ 
      success: false, 
      error: error.message
    });
  }
});

// 수동 테스트 엔드포인트
app.post("/test", async (req, res) => {
  try {
    debugLog("수동 테스트 API 호출");
    await testMCPConnection();
    res.json({ success: true, message: "테스트 완료" });
  } catch (error) {
    debugLog("수동 테스트 실패", { error: error.message });
    res.status(500).json({ 
      success: false, 
      error: error.message
    });
  }
});

app.get("/tools", async (req, res) => {
  try {
    debugLog("도구 목록 API 호출");
    
    if (!mcpInitialized) {
      return res.status(503).json({
        error: "MCP가 아직 초기화되지 않음",
        mcpReady: mcpReady,
        mcpInitialized: mcpInitialized
      });
    }
    
    const response = await sendMCPRequest({
      jsonrpc: "2.0",
      id: `tools-list-${Date.now()}`,
      method: "tools/list",
      params: {}
    });
    
    debugLog("도구 목록 응답", response);
    
    if (response.error) {
      throw new Error(response.error.message);
    }
    
    res.json(response.result || response);
  } catch (error) {
    debugLog("도구 목록 조회 실패", { error: error.message });
    console.error("도구 목록 조회 실패:", error);
    res.status(503).json({
      error: error.message,
      mcpReady: mcpReady,
      mcpInitialized: mcpInitialized
    });
  }
});

// JSON-RPC 처리
app.post("/", async (req, res) => {
  try {
    const request = req.body;
    debugLog("JSON-RPC 요청 수신", request);
    
    if (!request || !request.id) {
      return res.status(400).json({
        jsonrpc: "2.0",
        id: null,
        error: {
          code: -32600,
          message: "잘못된 요청: id 필드 누락"
        }
      });
    }

    if (!mcpInitialized && request.method !== "initialize") {
      return res.status(503).json({
        jsonrpc: "2.0",
        id: request.id,
        error: {
          code: -32002,
          message: "MCP가 아직 초기화되지 않음"
        }
      });
    }

    console.log(`[API 요청] ${JSON.stringify(request)}`);
    
    const response = await sendMCPRequest(request);
    debugLog("JSON-RPC 응답 전송", response);
    res.json(response);
    
  } catch (error) {
    debugLog("JSON-RPC 요청 처리 오류", { error: error.message });
    console.error("요청 처리 오류:", error);
    res.status(500).json({
      jsonrpc: "2.0",
      id: req.body?.id || null,
      error: {
        code: -32000,
        message: `서버 오류: ${error.message}`,
        data: {
          mcpReady: mcpReady,
          mcpInitialized: mcpInitialized,
          processRunning: childProcess && !childProcess.killed
        }
      }
    });
  }
});

// 도구 실행 엔드포인트
app.post("/tools/:toolName", async (req, res) => {
  try {
    const { toolName } = req.params;
    const toolArgs = req.body || {};
    
    debugLog("도구 실행 요청", { toolName: toolName, args: toolArgs });
    
    if (!mcpInitialized) {
      return res.status(503).json({
        error: "MCP가 아직 초기화되지 않음",
        tool: toolName
      });
    }
    
    const response = await sendMCPRequest({
      jsonrpc: "2.0",
      id: `tool-${toolName}-${Date.now()}`,
      method: "tools/call",
      params: {
        name: toolName,
        arguments: toolArgs
      }
    });
    
    debugLog("도구 실행 응답", response);
    
    if (response.error) {
      throw new Error(response.error.message);
    }
    
    res.json(response.result || response);
  } catch (error) {
    debugLog("도구 실행 실패", { toolName: req.params.toolName, error: error.message });
    console.error(`도구 실행 실패 (${req.params.toolName}):`, error);
    res.status(500).json({
      error: error.message,
      tool: req.params.toolName
    });
  }
});

// 서버 시작
childProcess = startMCPProcess();

// 종료 처리
process.on("SIGINT", () => {
  debugLog("SIGINT 신호 수신");
  console.log("🛑 서버 종료 중...");
  isShuttingDown = true;
  if (childProcess) {
    childProcess.kill();
  }
  process.exit(0);
});

process.on("SIGTERM", () => {
  debugLog("SIGTERM 신호 수신");
  console.log("🛑 서버 종료 중...");
  isShuttingDown = true;
  if (childProcess) {
    childProcess.kill();
  }
  process.exit(0);
});

app.listen(port, () => {
  debugLog("Express 서버 시작", { port: port });
  console.log(`🚀 OpenCV MCP Proxy 서버가 ${port}번 포트에서 실행 중`);
});