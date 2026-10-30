const { app, BrowserWindow, ipcMain } = require('electron')
const path = require('path')

// ── Dependencias nativas (pueden fallar si no están instaladas) ──────────────
let mouse, Button, uIOhook

try {
  const nut = require('@nut-tree-fork/nut-js')
  mouse  = nut.mouse
  Button = nut.Button
} catch (e) {
  console.warn('[nut-js] No disponible:', e.message)
}

try {
  uIOhook = require('uiohook-napi').uIOhook
} catch (e) {
  console.warn('[uiohook-napi] No disponible:', e.message)
}

// ── Ventana principal ─────────────────────────────────────────────────────────
let win

function createWindow() {
  win = new BrowserWindow({
    width: 920,
    height: 680,
    minWidth: 760,
    minHeight: 560,
    backgroundColor: '#0f1117',
    titleBarStyle: process.platform === 'darwin' ? 'hiddenInset' : 'default',
    autoHideMenuBar: true,
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false,
    },
  })
  win.loadFile('index.html')
}

app.whenReady().then(createWindow)
app.on('window-all-closed', () => {
  stopInactivityMonitor()
  if (process.platform !== 'darwin') app.quit()
})
app.on('activate', () => {
  if (BrowserWindow.getAllWindows().length === 0) createWindow()
})

// ── Estado del generador ──────────────────────────────────────────────────────
let generatorTimer   = null
let generatorRunning = false
let startedAt        = null
let lastTickAt       = null
let currentInterval  = 120

// ── Estado del monitor de inactividad ────────────────────────────────────────
let lastActivity       = Date.now()
let inactivityWatcher  = null
let inactivityActive   = false

// ── IPC: configuración → main ─────────────────────────────────────────────────

ipcMain.handle('start-generator', async (_, { interval, action, eventType, quantity }) => {
  if (generatorRunning) return { ok: false, msg: 'Ya está en ejecución' }

  currentInterval  = interval * 1000
  generatorRunning = true
  startedAt        = Date.now()
  lastTickAt       = Date.now()

  generatorTimer = setInterval(async () => {
    lastTickAt = Date.now()
    const result = await fireEvent(action, eventType, quantity)
    win?.webContents.send('tick', result)
  }, currentInterval)

  return { ok: true }
})

ipcMain.handle('stop-generator', () => {
  stopGenerator('Detenido por el usuario')
  return { ok: true }
})

ipcMain.handle('start-inactivity', (_, { idleSecs }) => {
  return startInactivityMonitor(idleSecs)
})

ipcMain.handle('stop-inactivity', () => {
  stopInactivityMonitor()
  return { ok: true }
})

ipcMain.handle('get-status', () => ({
  generatorRunning,
  inactivityActive,
  nutAvailable:    !!mouse,
  uiohookAvailable: !!uIOhook,
}))

// ── Contadores para la UI ─────────────────────────────────────────────────────
setInterval(() => {
  if (!win) return
  const now = Date.now()

  if (generatorRunning && startedAt !== null) {
    const elapsed   = Math.floor((now - startedAt) / 1000)
    const remaining = Math.max(0, Math.floor((currentInterval - (now - lastTickAt)) / 1000))
    win.webContents.send('timers', { elapsed, remaining })
  }

  if (inactivityActive && !generatorRunning) {
    const idleSecs = Math.floor((now - lastActivity) / 1000)
    win.webContents.send('idle-timer', { idleSecs })
  }
}, 1000)

// ── Generar evento ────────────────────────────────────────────────────────────
const BUTTON_MAP = {
  izquierdo: 'LEFT',
  derecho:   'RIGHT',
  central:   'MIDDLE',
}

async function fireEvent(action, eventType, quantity) {
  if (action !== 'Generar evento') {
    return { event: 'Evento registrado', detail: 'Sin acción en el sistema' }
  }
  if (!mouse) {
    return { event: 'Evento (sin efecto)', detail: '@nut-tree-fork/nut-js no instalado' }
  }
  try {
    const pos = await mouse.getPosition()
    const btn = Button[BUTTON_MAP[eventType] || 'LEFT']
    for (let i = 0; i < quantity; i++) {
      await mouse.click(btn)
    }
    return {
      event:  'Evento generado',
      detail: `Tipo: ${eventType} · cantidad: ${quantity} · posición: (${pos.x}, ${pos.y})`,
    }
  } catch (err) {
    // Failsafe: nut-js lanza error si el cursor está en esquina
    stopGenerator('⚡ Failsafe activado — generador detenido')
    win?.webContents.send('failsafe')
    return { event: '⚡ Failsafe', detail: err.message }
  }
}

function stopGenerator(reason = 'Detenido') {
  if (generatorTimer) {
    clearInterval(generatorTimer)
    generatorTimer = null
  }
  generatorRunning = false
  startedAt        = null
  lastTickAt       = null
  win?.webContents.send('generator-stopped', { reason })
}

// ── Monitor de inactividad ────────────────────────────────────────────────────
function startInactivityMonitor(idleSecs) {
  if (!uIOhook) {
    return { ok: false, msg: 'uiohook-napi no instalado — npm install uiohook-napi' }
  }
  try {
    uIOhook.on('mousemove', () => { lastActivity = Date.now() })
    uIOhook.on('mousedown', () => { lastActivity = Date.now() })
    uIOhook.on('wheel',     () => { lastActivity = Date.now() })
    uIOhook.on('keydown',   () => { lastActivity = Date.now() })
    uIOhook.start()
  } catch (err) {
    return { ok: false, msg: `Error al iniciar monitor: ${err.message}` }
  }

  lastActivity     = Date.now()
  inactivityActive = true
  const threshold  = idleSecs * 1000

  inactivityWatcher = setInterval(() => {
    const idle = Date.now() - lastActivity

    if (idle >= threshold && !generatorRunning) {
      win?.webContents.send('auto-start')
      // Arranca generador — la UI envía start-generator por IPC
    }

    if (idle < 2000 && generatorRunning) {
      win?.webContents.send('auto-stop')
    }
  }, 1000)

  return { ok: true }
}

function stopInactivityMonitor() {
  if (inactivityWatcher) {
    clearInterval(inactivityWatcher)
    inactivityWatcher = null
  }
  inactivityActive = false
  try { uIOhook?.stop() } catch (_) {}
}
