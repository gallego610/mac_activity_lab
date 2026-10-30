const { contextBridge, ipcRenderer } = require('electron')

contextBridge.exposeInMainWorld('api', {
  // Acciones
  startGenerator:   (cfg)      => ipcRenderer.invoke('start-generator', cfg),
  stopGenerator:    ()         => ipcRenderer.invoke('stop-generator'),
  startInactivity:  (cfg)      => ipcRenderer.invoke('start-inactivity', cfg),
  stopInactivity:   ()         => ipcRenderer.invoke('stop-inactivity'),
  getStatus:        ()         => ipcRenderer.invoke('get-status'),

  // Eventos desde main → renderer
  onTick:           (cb) => ipcRenderer.on('tick',              (_, d) => cb(d)),
  onTimers:         (cb) => ipcRenderer.on('timers',            (_, d) => cb(d)),
  onIdleTimer:      (cb) => ipcRenderer.on('idle-timer',        (_, d) => cb(d)),
  onGeneratorStopped:(cb)=> ipcRenderer.on('generator-stopped', (_, d) => cb(d)),
  onAutoStart:      (cb) => ipcRenderer.on('auto-start',        ()     => cb()),
  onAutoStop:       (cb) => ipcRenderer.on('auto-stop',         ()     => cb()),
  onFailsafe:       (cb) => ipcRenderer.on('failsafe',          ()     => cb()),
})
