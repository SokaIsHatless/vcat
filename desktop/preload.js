const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('catWindow', {
  moveBy: (dx, dy) => ipcRenderer.send('window-move-by', { dx, dy }),
  setHeight: (height) => ipcRenderer.send('window-set-height', { height }),
});
