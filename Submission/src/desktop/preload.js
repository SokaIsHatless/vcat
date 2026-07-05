const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('catWindow', {
  moveBy: (dx, dy) => ipcRenderer.send('window-move-by', { dx, dy }),
  setHeight: (height) => ipcRenderer.send('window-set-height', { height }),
});

contextBridge.exposeInMainWorld('catStorage', {
  hasSavedCutout: () => ipcRenderer.invoke('cat-has-saved-cutout'),
  saveCutout: (arrayBuffer) => ipcRenderer.invoke('cat-save-cutout', arrayBuffer),
  getCutoutUrl: () => ipcRenderer.invoke('cat-get-cutout-url'),
  deleteCutout: () => ipcRenderer.invoke('cat-delete-cutout'),
});
