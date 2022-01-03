function set_limit_rate() {
    var status_url = '/limit_rate/' + bw_limit.value * 1024
    var request = new XMLHttpRequest()
    request.open('GET', status_url)
    request.responseType = 'json'
    request.send()
    limit_label.value = bw_limit.value
}
