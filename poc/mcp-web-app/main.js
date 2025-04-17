const { app, BrowserWindow, ipcMain, dialog } = require('electron');
const path = require('path');
const { fork } = require('child_process');
const axios = require('axios');
require('dotenv').config();

let serverProcess = null;
let mainWindow;

console.log('✅ main.js started');

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1000,
    height: 700,
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
    },
  });
  mainWindow.loadFile('renderer/index.html');
}

function startMCPServer() {
  try {
    const serverPath = path.join(__dirname, 'mcp-server.js');
    console.log('[MCP] server path:', serverPath);
    serverProcess = fork(serverPath);
    serverProcess.on('error', (err) =>
      console.error('[MCP] server failed to start:', err)
    );
    serverProcess.on('exit', (code, signal) =>
      console.warn(`[MCP] server exited (code: ${code}, signal: ${signal})`)
    );
    console.log('[MCP] server started as child process');
  } catch (e) {
    console.error('[MCP] launch error:', e);
  }
}

async function decideToolByClaude(command, projectPath) {
  const prompt = `
You are an AI assistant that maps user commands to the appropriate MCP server method.

[User Command]
"${command}"

[Project Path]
${projectPath}

[Available Methods]
- execute_command → requires: { cwd, command }
- edit_file → requires: { path, new_content }
- directory_tree → requires: { path }
- read_files → requires: { path, ext }
- ask_llm → requires: { prompt, llm }

[Output Format]
Respond ONLY with a JSON object like this:
{
  "method": "METHOD_NAME",
  "params": {
    // required fields for that method
  }
}

Example:
{
  "method": "execute_command",
  "params": {
    "cwd": "${projectPath}",
    "command": "npm test"
  }
}

⚠️ Very Important:
MCP will execute one method at a time and handle next steps itself.  
You must return ONLY the **first MCP method** that should be executed.  
DO NOT include any future steps, chained method calls, or explanations.  
Return exactly ONE valid JSON object. No extra text. No Markdown.
`;

  const response = await axios.post(
    'https://api.anthropic.com/v1/messages',
    {
      model: 'claude-3-opus-20240229',
      max_tokens: 1024,
      messages: [{ role: 'user', content: prompt }],
    },
    {
      headers: {
        'x-api-key': process.env.CLAUDE_API_KEY,
        'anthropic-version': '2023-06-01',
        'Content-Type': 'application/json',
      },
    }
  );

  const contentRaw = response.data.content;
  const content = Array.isArray(contentRaw)
    ? contentRaw.map((c) => c.text || '').join('')
    : contentRaw;

  console.log('[Claude raw response]', content);

  const start = content.indexOf('{');
  const end = content.lastIndexOf('}');
  const jsonText = content.slice(start, end + 1);
  return JSON.parse(jsonText);
}

async function askLLMWithFileContext(userCommand, files, projectPath) {
  const filePreview = files
    .map((f) => `${f.path}\n${f.content.slice(0, 10000)}...`)
    .join('\n\n');

  const prompt = `
[User Command]
"${userCommand}"

[File Contents Preview]
${filePreview}

Based on the command and files above, respond with:

If you want to return a natural language response only:
{
  "method": "default",
  "response": "요약된 내용 또는 분석 결과를 작성하세요."
}

If you want to modify the code:
{
  "method": "edit_file",
  "params": {
    "path": "파일 경로",
    "new_content": "전체 수정된 파일 내용"
  }
}

Respond ONLY with one valid JSON object. No extra text. No Markdown.
`;

  const llmRes = await axios.post(`${process.env.MCP_SERVER}/rpc`, {
    method: 'ask_llm',
    params: { prompt, llm: 'claude' },
  });

  const raw = llmRes.data.result;

  // Claude 응답이 배열인 경우 text 추출
  const fullText = Array.isArray(raw)
    ? raw
        .map((obj) => obj.text)
        .join('')
        .trim()
    : String(raw).trim();

  console.log('[Claude Raw Response]', fullText);

  try {
    const start = fullText.indexOf('{');
    const end = fullText.lastIndexOf('}');
    const jsonText = fullText.slice(start, end + 1);
    const parsed = JSON.parse(jsonText);
    console.log('[Parsed JSON]', parsed);
    return parsed;
  } catch (e) {
    console.warn('[JSON 파싱 실패]', e.message);
    return {
      method: 'default',
      response: fullText,
    };
  }
}

ipcMain.handle('run-command', async (event, command) => {
  try {
    const initial = await decideToolByClaude(
      command.command,
      command.projectPath
    );
    console.log('[LLM] Claude selected method:', initial);

    if (initial.method === 'read_files') {
      const readRes = await axios.post(`${process.env.MCP_SERVER}/rpc`, {
        method: 'read_files',
        params: initial.params,
      });

      const files = readRes.data.result;
      const decision = await askLLMWithFileContext(
        command.command,
        files,
        command.projectPath
      );
      console.log('[LLM Decision After File Read]', decision);

      if (decision.method === 'edit_file') {
        const editRes = await axios.post(`${process.env.MCP_SERVER}/rpc`, {
          method: 'edit_file',
          params: decision.params,
        });
        return { type: 'edit', result: editRes.data.result };
      } else {
        return {
          type: 'default',
          result: decision.response || decision.result,
        };
      }
    }

    // 기본 처리 (예: directory_tree, execute_command 등)
    const directRes = await axios.post(`${process.env.MCP_SERVER}/rpc`, {
      method: initial.method,
      params: initial.params,
    });

    return { type: 'default', result: directRes.data.result };
  } catch (e) {
    console.error('[run-command error]', e.message);
    return { error: e.message };
  }
});

ipcMain.handle('select-folder', async () => {
  const result = await dialog.showOpenDialog({ properties: ['openDirectory'] });
  return result.canceled || result.filePaths.length === 0
    ? null
    : result.filePaths[0];
});

app.whenReady().then(() => {
  startMCPServer();
  createWindow();
});

app.on('will-quit', () => {
  if (serverProcess) serverProcess.kill();
});
