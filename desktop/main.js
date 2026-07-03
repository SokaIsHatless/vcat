const { app, BrowserWindow, ipcMain, screen } = require('electron');
const fs = require('fs');
const path = require('path');
const { pathToFileURL } = require('url');

const WINDOW_WIDTH = 320;
const WINDOW_MIN_HEIGHT = 300;
const WINDOW_MAX_HEIGHT = 720;
const CAT_CUTOUT_FILENAME = 'cat-cutout.png';

let mainWindow;

function getCutoutPath() {
  return path.join(app.getPath('userData'), CAT_CUTOUT_FILENAME);
}

function clampToWorkArea(x, y, width, height) {
  const display = screen.getDisplayNearestPoint({
    x: Math.round(x + width / 2),
    y: Math.round(y + height / 2),
  });
  const { workArea } = display;

  const minX = workArea.x;
  const minY = workArea.y;
  const maxX = workArea.x + workArea.width - width;
  const maxY = workArea.y + workArea.height - height;

  return {
    x: Math.min(Math.max(x, minX), maxX),
    y: Math.min(Math.max(y, minY), maxY),
  };
}

function setWindowPositionClamped(x, y) {
  if (!mainWindow) return;
  const [width, height] = mainWindow.getContentSize();
  const clamped = clampToWorkArea(x, y, width, height);
  mainWindow.setPosition(clamped.x, clamped.y);
}

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

  mainWindow.on('moved', () => {
    if (!mainWindow) return;
    const [x, y] = mainWindow.getPosition();
    const [width, height] = mainWindow.getContentSize();
    const clamped = clampToWorkArea(x, y, width, height);
    if (clamped.x !== x || clamped.y !== y) {
      mainWindow.setPosition(clamped.x, clamped.y);
    }
  });
}

ipcMain.handle('cat-has-saved-cutout', () => {
  return fs.existsSync(getCutoutPath());
});

ipcMain.handle('cat-save-cutout', (_event, arrayBuffer) => {
  const filePath = getCutoutPath();
  fs.mkdirSync(path.dirname(filePath), { recursive: true });
  fs.writeFileSync(filePath, Buffer.from(arrayBuffer));
  return pathToFileURL(filePath).href;
});

ipcMain.handle('cat-get-cutout-url', () => {
  const filePath = getCutoutPath();
  if (!fs.existsSync(filePath)) {
    return null;
  }
  return pathToFileURL(filePath).href;
});

ipcMain.handle('cat-delete-cutout', () => {
  const filePath = getCutoutPath();
  if (fs.existsSync(filePath)) {
    fs.unlinkSync(filePath);
  }
  return true;
});

ipcMain.on('window-move-by', (_event, { dx, dy }) => {
  if (!mainWindow) return;
  const [x, y] = mainWindow.getPosition();
  setWindowPositionClamped(x + dx, y + dy);
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
  setWindowPositionClamped(x, y - delta);
});

app.whenReady().then(createWindow);

app.on('window-all-closed', () => {
  app.quit();
});
