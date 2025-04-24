const { contextBridge, ipcRenderer } = require('electron');

/* nonce를 CSP에 삽입할 수 있도록 window에 제공 */
const nonce = crypto.randomUUID();
process.once('loaded', () => {
  Object.defineProperty(window, '__nonce', { value: nonce });
});

contextBridge.exposeInMainWorld('api', {
  selectProjectFolder: () => ipcRenderer.invoke('select-folder'),
  sendCommand:         (text) => ipcRenderer.invoke('run-command', text)
});
