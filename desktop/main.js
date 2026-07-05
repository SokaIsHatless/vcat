const {
  app,
  BrowserWindow,
  ipcMain,
  screen,
  Tray,
  Menu,
  nativeImage,
  shell,
} = require('electron');
const fs = require('fs');
const path = require('path');
const { pathToFileURL } = require('url');

const WINDOW_WIDTH = 320;
const WINDOW_MIN_HEIGHT = 300;
const WINDOW_MAX_HEIGHT = 720;
const CAT_CUTOUT_FILENAME = 'cat-cutout.png';

let mainWindow;
let tray = null;
let catVisible = true;

function getCutoutPath() {
  return path.join(app.getPath('userData'), CAT_CUTOUT_FILENAME);
}

function getTrayIcon() {
  const iconPath = path.join(__dirname, 'logo.png');
  const icon = nativeImage.createFromPath(iconPath);
  return icon.resize({ width: 16, height: 16 });
}

function positionWindowAtCenter() {
  if (!mainWindow) return;

  const { workArea } = screen.getPrimaryDisplay();
  const { width: w, height: h } = mainWindow.getBounds();
  const centerX = Math.round(workArea.x + (workArea.width - w) / 2);
  const centerY = Math.round(workArea.y + (workArea.height - h) / 2);

  mainWindow.setPosition(centerX, centerY);
}

function centerCat() {
  if (!mainWindow) return;

  mainWindow.show();
  mainWindow.moveTop();
  positionWindowAtCenter();

  catVisible = true;
  rebuildTrayMenu();
}

function setCatVisible(visible) {
  if (!mainWindow) return;

  catVisible = visible;
  if (visible) {
    mainWindow.show();
  } else {
    mainWindow.hide();
  }
  rebuildTrayMenu();
}

function rebuildTrayMenu() {
  if (!tray) return;

  const menu = Menu.buildFromTemplate([
    {
      label: catVisible ? 'Hide cat' : 'Show cat',
      click: () => setCatVisible(!catVisible),
    },
    {
      label: 'Center cat',
      click: () => centerCat(),
    },
    { type: 'separator' },
    {
      label: 'Quit',
      click: () => {
        app.isQuitting = true;
        app.quit();
      },
    },
  ]);

  tray.setContextMenu(menu);
}

function createTray() {
  tray = new Tray(getTrayIcon());
  tray.setToolTip('Cat Overlord');

  tray.on('click', () => {
    centerCat();
  });

  rebuildTrayMenu();
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

ipcMain.on('window-center', () => {
  positionWindowAtCenter();
});

ipcMain.handle('shell-open-path', async (_event, filePath) => {
  if (!filePath || typeof filePath !== 'string') {
    return 'Invalid file path';
  }
  return shell.openPath(filePath);
});

app.whenReady().then(() => {
  createWindow();
  createTray();
});

app.on('window-all-closed', () => {
  // Tray keeps the app alive when the cat window is hidden.
});

app.on('before-quit', () => {
  app.isQuitting = true;
  if (tray) {
    tray.destroy();
    tray = null;
  }
});
