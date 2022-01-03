function trigger(action) {
  var request = new XMLHttpRequest()
  request.open('GET', '/' + action)
  request.responseType = 'json'
  request.send()
  request.onload = function() {
    var response = request.response
    if (request.status == 200) {
      update_button_label(action)
    }
  }
}

function update_button_label(action) {
  var button = document.getElementById('pause_button');
  if (button.value == action) {
    if (action == 'pause') {
      button.value = 'resume'
      button.innerHTML = '<i class="bi bi-play-fill"></i> Fortsetzen';
    }
    if (action == 'resume') {
      button.value = 'pause'
      button.innerHTML = '<i class="bi bi-pause"></i> Pausieren';
    }
  }
}

function toggle_pause() {
  var button = document.getElementById('pause_button');
  if (button.value == 'pause') {
    trigger('pause')
  } else {
    trigger('resume')
  }
}
