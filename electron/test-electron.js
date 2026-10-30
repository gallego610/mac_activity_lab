const { app, BrowserWindow } = require('electron')

console.log('app:', app)
console.log('app.whenReady:', app ? app.whenReady : 'undefined')

if (app) {
  app.whenReady().then(() => {
    console.log('Electron ready!')
    app.quit()
  })
} else {
  console.log('ERROR: app is undefined')
}
