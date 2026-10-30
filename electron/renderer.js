// ── Estado local ──────────────────────────────────────────────────────────────
let eventCount    = 0
let generatorOn   = false
let autoOn        = false
let logData       = []
let rowIndex      = 0

// ── Referencias DOM ───────────────────────────────────────────────────────────
const btnStart  = document.getElementById('btn-start')
const btnAuto   = document.getElementById('btn-auto')
const btnStop   = document.getElementById('btn-stop')
const btnExport = document.getElementById('btn-export')
const btnClear  = document.getElementById('btn-clear')
const logBody   = document.getElementById('log-body')
const cat       = document.getElementById('cat')
const status    = document.getElementById('status-badge')
const bCount    = document.getElementById('b-count')
const bElapsed  = document.getElementById('b-elapsed')
const bNext     = document.getElementById('b-next')
const bIdle     = document.getElementById('b-idle')
const nutWarn   = document.getElementById('nut-warn')
const uioWarn   = document.getElementById('uio-warn')

// ── Animación gatito ──────────────────────────────────────────────────────────
const CAT_IDLE    = '😴 zzz'
const CAT_FRAMES  = ['😺 ～', '😸 ♪', '🐱 ！', '😻 ★', '😺 ～', '🐱 ♫']
let catFrame      = 0
let catTimer      = null

function startCat() {
  if (catTimer) return
  catTimer = setInterval(() => {
    cat.textContent = CAT_FRAMES[catFrame % CAT_FRAMES.length]
    catFrame++
  }, 400)
}
function stopCat() {
  clearInterval(catTimer)
  catTimer    = null
  catFrame    = 0
  cat.textContent = CAT_IDLE
}

// ── Helpers formato tiempo ────────────────────────────────────────────────────
function fmtHMS(secs) {
  const h = Math.floor(secs / 3600)
  const m = Math.floor((secs % 3600) / 60)
  const s = secs % 60
  return `${String(h).padStart(2,'0')}:${String(m).padStart(2,'0')}:${String(s).padStart(2,'0')}`
}
function fmtMS(secs) {
  const m = Math.floor(secs / 60)
  const s = secs % 60
  return `${String(m).padStart(2,'0')}:${String(s).padStart(2,'0')}`
}

// ── Log ───────────────────────────────────────────────────────────────────────
function addRow(event, detail) {
  const stamp = new Date().toISOString().replace('T', ' ').slice(0, 19)
  logData.push({ timestamp: stamp, event, detail })
  eventCount++
  bCount.textContent = eventCount

  const row = document.createElement('div')
  row.className = 'log-row'
  if (rowIndex % 2 === 0) row.style.background = 'var(--card)'
  row.innerHTML = `
    <span class="ts">${stamp}</span>
    <span class="ev">${event}</span>
    <span class="det">${detail}</span>
  `
  logBody.appendChild(row)
  logBody.scrollTop = logBody.scrollHeight
  rowIndex++
}

// ── Verificar disponibilidad al cargar ────────────────────────────────────────
window.addEventListener('DOMContentLoaded', async () => {
  const s = await window.api.getStatus()
  if (!s.nutAvailable)     nutWarn.style.display = 'block'
  if (!s.uiohookAvailable) uioWarn.style.display = 'block'
})

// ── Iniciar generador ─────────────────────────────────────────────────────────
async function startGenerator() {
  const cfg = {
    interval:  parseInt(document.getElementById('interval').value)  || 120,
    action:    document.getElementById('action').value,
    eventType: document.getElementById('event-type').value,
    quantity:  parseInt(document.getElementById('quantity').value)  || 1,
  }
  const res = await window.api.startGenerator(cfg)
  if (!res.ok) { addRow('Error', res.msg); return }

  generatorOn = true
  setStatus('Generando eventos', 'var(--green)', '#0f1117')
  btnStart.disabled = true
  btnStop.disabled  = false
  startCat()
  addRow('Generador iniciado', `Intervalo: ${cfg.interval} s · acción: ${cfg.action}`)
}

async function stopGenerator() {
  await window.api.stopGenerator()
  // La UI se actualiza vía onGeneratorStopped
}

// ── Inicio automático ─────────────────────────────────────────────────────────
async function toggleAuto() {
  if (!autoOn) {
    const idleSecs = parseInt(document.getElementById('idle-secs').value) || 180
    const res = await window.api.startInactivity({ idleSecs })
    if (!res.ok) { addRow('Error', res.msg); return }
    autoOn = true
    btnAuto.textContent = '⏱  Cancelar automático'
    btnAuto.style.background = 'var(--border)'
    setStatus('En espera', 'var(--orange)', '#0f1117')
    addRow('Inicio automático activado', `Espera previa: ${idleSecs} s`)
  } else {
    await window.api.stopInactivity()
    autoOn = false
    btnAuto.textContent = '⏱  Inicio automático'
    btnAuto.style.background = 'var(--orange)'
    bIdle.textContent = '--:--'
    if (!generatorOn) setStatus('Inactivo', 'var(--border)', 'var(--dim)')
    addRow('Inicio automático desactivado', '')
  }
}

function setStatus(text, bg, color) {
  status.textContent        = text
  status.style.background   = bg
  status.style.color        = color
}

// ── Eventos IPC desde main ────────────────────────────────────────────────────
window.api.onTick(({ event, detail }) => {
  addRow(event, detail)
})

window.api.onTimers(({ elapsed, remaining }) => {
  bElapsed.textContent = fmtHMS(elapsed)
  bNext.textContent    = fmtMS(remaining)
})

window.api.onIdleTimer(({ idleSecs }) => {
  const threshold = parseInt(document.getElementById('idle-secs').value) || 180
  const remaining = Math.max(0, threshold - idleSecs)
  bIdle.textContent = fmtMS(remaining)
})

window.api.onGeneratorStopped(({ reason }) => {
  generatorOn = false
  btnStart.disabled = false
  btnStop.disabled  = true
  bNext.textContent = '--:--'
  stopCat()
  if (!autoOn) setStatus('Inactivo', 'var(--border)', 'var(--dim)')
  else         setStatus('En espera', 'var(--orange)', '#0f1117')
  addRow('Generador detenido', reason)
})

window.api.onAutoStart(async () => {
  addRow('▶ Generador iniciado', 'Inicio automático por temporizador')
  await startGenerator()
})

window.api.onAutoStop(async () => {
  addRow('⏹ Generador pausado', 'En espera — temporizador reiniciado')
  await window.api.stopGenerator()
})

window.api.onFailsafe(() => {
  addRow('⚡ Failsafe activado', 'Generador detenido')
})

// ── Exportar ──────────────────────────────────────────────────────────────────
btnExport.addEventListener('click', () => {
  if (!logData.length) return
  const blob = new Blob([JSON.stringify(logData, null, 2)], { type: 'application/json' })
  const url  = URL.createObjectURL(blob)
  const a    = document.createElement('a')
  a.href     = url
  a.download = 'activity_event_generator_log.json'
  a.click()
  URL.revokeObjectURL(url)
})

// ── Limpiar ───────────────────────────────────────────────────────────────────
btnClear.addEventListener('click', () => {
  if (generatorOn) return
  logData       = []
  eventCount    = 0
  rowIndex      = 0
  bCount.textContent   = '0'
  bElapsed.textContent = '00:00:00'
  bNext.textContent    = '--:--'
  logBody.innerHTML    = ''
})

// ── Listeners botones ─────────────────────────────────────────────────────────
btnStart.addEventListener('click', startGenerator)
btnStop.addEventListener('click',  stopGenerator)
btnAuto.addEventListener('click',  toggleAuto)
