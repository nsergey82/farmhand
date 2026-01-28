let sessionid = ''

function block_for_auth(sid, callback) {
  fetch('https://ppauth.onrender.com/ename/' + sid).then(res => {
    res.text().then(name => {
      callback(name)
    })
  })
}

function present_qr(qr) {
  const div = document.createElement('div')
  div.innerHTML = qr + '<br/>Scan with eid app to authenticate'
  document.body.appendChild(div)
}

function get_qr_for_ename(callback) {
  // note, the endpoint can be spun down,
  // and so this may take about a minute...
  console.log('starting fetch qr')
  fetch('https://ppauth.onrender.com/headless/farmhand').then(res => {
    console.log('got qr from ppauth')
    res.json().then(data => {
      sessionid = data['session']
      present_qr(data['qr'])
      setTimeout(block_for_auth, 50, sessionid, callback)
    })
  })
}
