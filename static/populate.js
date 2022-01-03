function get_status() {
    var status_url = '/status'
    var request = new XMLHttpRequest()
    request.open('GET', status_url)
    request.responseType = 'json'
    request.send()
    request.onload = function() {
      var status_data = request.response
      populate_status(status_data)
    }
}

function add_progress_bar(status_data, parent) {
  // populate file progress
  var _row = document.createElement('div')
  _row.className = 'row'
  parent.append(_row)

  var _col = document.createElement('div')
  _col.className = 'col'
  _row.append(_col)

  var _progress = document.createElement('div')
  _progress.className = 'progress'
  _col.append(_progress)

  var _progress_bar = document.createElement('div')
  _progress_bar.className = 'progress-bar progress-bar-striped progress-bar-animated bg-success'
  _progress.append(_progress_bar)

  // var d = new Date();
  // var percent = Math.trunc(d.getSeconds() / 60 * 100);
  // _progress_bar.style.width = percent + '%'
  _progress_bar.style.width = status_data['current_percent'] + '%'
}

function populate_elements(status_data) {
  // -- download list --
  var elements_list = document.getElementById('elements_list')
  // empty download list view
  var lis = document.querySelectorAll('#elements_list li');
  for (var i=0; li=lis[i]; i++) {
    li.parentNode.removeChild(li);
  }

  // populate it again ...
  var elements = status_data['elements']
  i = 1
  for (var key in elements) {
    if (elements.hasOwnProperty(key)) {
      var _li = document.createElement('li')
      _li.className = 'list-group-item d-flex justify-content-between align-items-start'
      elements_list.append(_li)

      var _container = document.createElement('div')
      _container.className = 'container'
      //_container.style.padding = 0
      _li.append(_container)

      var _row = document.createElement('div')
      _row.className = 'row'
      _container.append(_row)

      var _col8 = document.createElement('div')
      _col8.className = 'col-8'
      _row.append(_col8)

      var _span = document.createElement('span')
      _span.className = 'd-inline-block text-truncate'
      // _span.style.max_width = '80%'
      _span.innerHTML = elements[key].name
      _col8.append(_span)

      var _col4 = document.createElement('div')
      _col4.className = 'col-4 size'
      // _col4.style.text_align = 'right'
      _row.append(_col4)

      var _span = document.createElement('span')
      _span.innerHTML = elements[key].size
      _col4.append(_span)

      if (i == 1) {
        add_progress_bar(status_data, _container)
      }
      i++
    }
  }
}

function populate_status(status_data) {
  populate_elements(status_data)

  // populate download rate
  document.getElementById('download_rate').innerHTML = status_data['download_rate']

  if (status_data['pause'] == true) {
    update_button_label('pause')
  }
  else {
    update_button_label('resume')
  }

  // populate limit rate
  // set slider
}

function hide_alert() {
  setTimeout(function(){
    document.getElementById('alert_message').remove()
  }, 3000)
}

function update_status() {
  // automatically hide alert boxes after 3 seconds
  hide_alert()

  var frequency = 5000;  // refresh every 5 seconds
  get_status()
  setInterval(function(){
      if (!document.hidden) {
          get_status()
      }
   }, frequency)
}
