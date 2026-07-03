const { app, BrowserWindow, ipcMain, screen } = require('electron');
const fs = require('fs');
const path = require('path');
const { pathToFileURL } = require('url');

const WINDOW_WIDTH = 320;
const WINDOW_MIN_HEIGHT = 300;
const WINDOW_MAX_HEIGHT = 720;
const CAT_CUTOUT_FILENAME = 'cat-cutout.png';
const DEBUG_CLAMP = process.env.VCAT_DEBUG_CLAMP !== '0';

let mainWindow;

function getCutoutPath() {
  return path.join(app.getPath('userData'), CAT_CUTOUT_FILENAME);
}

/**
 * Clamp a desired top-left position so the full outer window (getBounds size)
 * stays inside the nearest display workArea (excludes taskbar).
 */
function computeClamp(desiredX, desiredY, sizeOverride = null) {
  const bounds = mainWindow.getBounds();
  const windowWidth = sizeOverride?.width ?? bounds.width;
  const windowHeight = sizeOverride?.height ?? bounds.height;

  const display = screen.getDisplayNearestPoint({
    x: Math.round(desiredX + windowWidth / 2),
    y: Math.round(desiredY + windowHeight / 2),
  });
  const { workArea } = display;

  const maxX = workArea.x + workArea.width - windowWidth;
  const maxY = workArea.y + workArea.height - windowHeight;

  const clampedX = Math.max(workArea.x, Math.min(desiredX, maxX));
  const clampedY = Math.max(workArea.y, Math.min(desiredY, maxY));

  if (DEBUG_CLAMP) {
    console.log('[clamp]', {
      workArea,
      window: { width: windowWidth, height: windowHeight },
      current: { x: bounds.x, y: bounds.y },
      desired: { x: desiredX, y: desiredY },
      clamped: { x: clampedX, y: clampedY },
      max: { x: maxX, y: maxY },
      outOfBounds: clampedX !== desiredX || clampedY !== desiredY,
    });
  }

  return { clampedX, clampedY, bounds };
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

  const bounds = mainWindow.getBounds();
  const desiredX = bounds.x + dx;
  const desiredY = bounds.y + dy;
  const { clampedX, clampedY } = computeClamp(desiredX, desiredY);

  // Only reposition when the clamped result differs from where we are now.
  // At the taskbar edge this skips redundant setPosition calls; elsewhere it moves freely.
  if (clampedX !== bounds.x || clampedY !== bounds.y) {
    mainWindow.setPosition(clampedX, clampedY);
  }
});

ipcMain.on('window-set-height', (_event, { height }) => {
  if (!mainWindow) return;

  const newHeight = Math.max(
    WINDOW_MIN_HEIGHT,
    Math.min(Math.ceil(height), WINDOW_MAX_HEIGHT),
  );
  const bounds = mainWindow.getBounds();
  const delta = newHeight - bounds.height;

  if (delta === 0) return;

  const desiredY = bounds.y - delta;
  const { clampedX, clampedY } = computeClamp(bounds.x, desiredY, {
    width: bounds.width,
    height: newHeight,
  });

  mainWindow.setBounds({
    x: clampedX,
    y: clampedY,
    width: bounds.width,
    height: newHeight,
  });
});

app.whenReady().then(createWindow);

app.on('window-all-closed', () => {
  app.quit();
});
