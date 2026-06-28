const { app, BrowserWindow, ipcMain } = require('electron');
const path = require('path');

const WINDOW_WIDTH = 320;
const WINDOW_MIN_HEIGHT = 300;
const WINDOW_MAX_HEIGHT = 720;

let mainWindow;

function createWindow() {
  mainWindow = new BrowserWindow({
    width: WINDOW_WIDTH,
    height: WINDOW_MIN_HEIGHT,
    transparent: true,
    frame: false,
    alwaysOnTop: true,
    skipTaskbar: true,
    resizable: false,
    hasShadow: false,
    backgroundColor: '#00000000',
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      nodeIntegration: false,
      contextIsolation: true,
    },
  });

  mainWindow.loadFile(path.join(__dirname, 'index.html'));
}

ipcMain.on('window-move-by', (_event, { dx, dy }) => {
  if (!mainWindow) return;
  const [x, y] = mainWindow.getPosition();
  mainWindow.setPosition(x + dx, y + dy);
});

ipcMain.on('window-set-height', (_event, { height }) => {
  if (!mainWindow) return;

  const newHeight = Math.max(
    WINDOW_MIN_HEIGHT,
    Math.min(Math.ceil(height), WINDOW_MAX_HEIGHT),
  );
  const [, oldHeight] = mainWindow.getContentSize();
  const delta = newHeight - oldHeight;

  if (delta === 0) return;

  const [x, y] = mainWindow.getPosition();
  mainWindow.setContentSize(WINDOW_WIDTH, newHeight);
  mainWindow.setPosition(x, y - delta);
});

app.whenReady().then(createWindow);

app.on('window-all-closed', () => {
  app.quit();
});
