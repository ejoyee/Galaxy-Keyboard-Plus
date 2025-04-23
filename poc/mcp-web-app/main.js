// main.js
require('dotenv').config();
const { app, BrowserWindow, ipcMain, dialog } = require('electron');
const path    = require('path');
const fs      = require('fs');
const spawn   = require('cross-spawn');
const axios   = require('axios');

// 1) 사용할 MCP 서버 매핑 (filesystem은 따로 기동)
const MCP_SERVERS = {
  github:                3001,
  everything:            3002,
  postgres:              3003,
  puppeteer:             3004,
  'sequential-thinking': 3005,
  'brave-search':        3006,
  gitlab:                3007,
  redis:                 3008,
  gdrive:                3009,
  slack:                 3010,
  'google-maps':         3011,
  memory:                3012,
};

// 2) 인증용 환경변수 매핑
const REQUIRED_ENV = {
  'brave-search':    'BRAVE_API_KEY',
  github:            'GITHUB_PERSONAL_ACCESS_TOKEN',
  slack:             'SLACK_BOT_TOKEN',
  'google-maps':     'GOOGLE_MAPS_API_KEY',
};

// 3) 전역 상태
let mainWindow;
let filesystemProc = null;
let selectedFolder = null;

// 4) Electron 윈도우 생성
function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1000,
    height: 700,
    webPreferences: { preload: path.join(__dirname, 'preload.js') },
  });
  mainWindow.loadFile('renderer/index.html');
}

// 5) MCP 서버(HTTP 모드) 자동 기동 (filesystem 제외)
function startMcpServers() {
  const isWin = process.platform === 'win32';
  for (const [pkg, port] of Object.entries(MCP_SERVERS)) {
    const needKey = REQUIRED_ENV[pkg];
    if (needKey && !process.env[needKey]) {
      console.warn(`[MCP:${pkg}] SKIP (missing env ${needKey})`);
      continue;
    }
    // 윈도우 cmd, 맥/리눅스는 그냥 바이너리
    const binName = isWin
      ? `mcp-server-${pkg}.cmd`
      : `mcp-server-${pkg}`;
    const binPath = path.join(__dirname, 'node_modules', '.bin', binName);
    if (!fs.existsSync(binPath)) {
      console.warn(`[MCP:${pkg}] SKIP (binary not found: ${binPath})`);
      continue;
    }
    console.log(`[MCP:${pkg}] STARTING on port ${port} (HTTP mode)`);
    const env = { ...process.env, MCP_PORT: port.toString() };
    const proc = spawn(
      binPath,
      ['--http', '--transport', 'http'],
      { stdio: ['ignore','pipe','pipe'], env, shell: true }
    );
    proc.stdout.on('data', buf =>
      buf.toString().split(/\r?\n/).forEach(line => {
        if (line) console.log(`[MCP:${pkg}] ${line}`);
      })
    );
    proc.stderr.on('data', buf =>
      buf.toString().split(/\r?\n/).forEach(line => {
        if (line) console.error(`[MCP:${pkg} ERR] ${line}`);
      })
    );
    proc.on('error', e =>
      console.error(`[MCP:${pkg}] failed to start`, e)
    );
    proc.on('exit', code =>
      console.log(`[MCP:${pkg}] exited with code ${code}`)
    );
  }
}

// 6) filesystem 서버(HTTP 모드) 기동
function startFilesystemServer(folderPath) {
  if (filesystemProc) {
    filesystemProc.kill();
    filesystemProc = null;
  }
  const isWin = process.platform === 'win32';
  const binName = isWin
    ? 'mcp-server-filesystem.cmd'
    : 'mcp-server-filesystem';
  const binPath = path.join(__dirname, 'node_modules', '.bin', binName);
  if (!fs.existsSync(binPath)) {
    console.warn(`[MCP:filesystem] SKIP (binary not found: ${binPath})`);
    return;
  }
  console.log(`[MCP:filesystem] STARTING on port 3000 for ${folderPath} (HTTP mode)`);
  selectedFolder = folderPath;

  const env = { ...process.env, MCP_PORT: '3000' };
  filesystemProc = spawn(
    binPath,
    ['--http', '--transport', 'http', folderPath],
    { stdio: ['ignore','pipe','pipe'], env, shell: true }
  );
  filesystemProc.stdout.on('data', buf =>
    buf.toString().split(/\r?\n/).forEach(line => {
      if (line) console.log(`[MCP:filesystem] ${line}`);
    })
  );
  filesystemProc.stderr.on('data', buf =>
    buf.toString().split(/\r?\n/).forEach(line => {
      if (line) console.error(`[MCP:filesystem ERR] ${line}`);
    })
  );
  filesystemProc.on('error', e =>
    console.error(`[MCP:filesystem] start error`, e)
  );
  filesystemProc.on('exit', code =>
    console.log(`[MCP:filesystem] exited with code ${code}`)
  );
}

// 7) OpenAI Function Calling으로 툴 매핑
async function decideToolByOpenAI(command) {
  const functions = [{
    name: 'call_mcp',
    description: 'Call an MCP server',
    parameters: {
      type: 'object',
      properties: {
        tool:   { type:'string' },
        method: { type:'string' },
        params: { type:'object' },
      },
      required: ['tool','method','params'],
    },
  }];

  const resp = await axios.post(
    'https://api.openai.com/v1/chat/completions',
    {
      model: 'gpt-4o-mini',
      messages: [
        {
          role: 'system',
          content: `Available tools: filesystem, ${Object.keys(MCP_SERVERS).join(', ')}`
        },
        { role: 'user', content: command }
      ],
      functions,
      function_call: 'auto',
    },
    { headers: { Authorization: `Bearer ${process.env.OPENAI_API_KEY}` } }
  );

  const msg = resp.data.choices[0].message;
  if (msg.function_call) {
    return JSON.parse(msg.function_call.arguments);
  } else {
    return { tool: null, method: null, response: msg.content };
  }
}

// 8) IPC 핸들러: UI → OpenAI → MCP RPC
ipcMain.handle('run-command', async (_, { command }) => {
  try {
    const { tool, method, params, response } = await decideToolByOpenAI(command);
    if (!tool) {
      return { type: 'default', result: response };
    }
    if (tool === 'filesystem' && !selectedFolder) {
      throw new Error('먼저 폴더를 선택해 주세요.');
    }
    const rpcParams = { ...params };
    if (!rpcParams.path && tool === 'filesystem') {
      rpcParams.path = selectedFolder;
    }
    const port = tool === 'filesystem' ? 3000 : MCP_SERVERS[tool];
    if (!port) throw new Error(`Unknown tool: ${tool}`);
    const rpcRes = await axios.post(`http://localhost:${port}/rpc`, {
      method, params: rpcParams
    });
    return { type: 'default', result: rpcRes.data.result };
  } catch (e) {
    console.error('[run-command error]', e);
    return { error: e.message };
  }
});

// 9) IPC 핸들러: 폴더 선택 → filesystem 서버 재기동
ipcMain.handle('select-folder', async () => {
  const result = await dialog.showOpenDialog({
    properties: ['openDirectory']
  });
  if (result.canceled || !result.filePaths.length) {
    return null;
  }
  const folderPath = result.filePaths[0];
  startFilesystemServer(folderPath);
  return folderPath;
});

// 10) 앱 초기화
app.whenReady().then(() => {
  // 초기 C:\ 경로로 filesystem 서버 기동
  startFilesystemServer('C:\\');

  startMcpServers();
  createWindow();
});
