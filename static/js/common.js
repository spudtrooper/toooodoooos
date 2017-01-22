function reload_(opt_url, opt_timeout) {
  setTimeout(function() {
    document.location = opt_url ? opt_url : String(document.location).replace(/#.*/, '');
  }, opt_timeout || 50);
}

function request(url, method, opt_data, opt_afterUrl, opt_timeout) {
  var data = opt_data || {};
  $.ajax({
    url: url,
    data: data,
    method: method,
    context: document.body
  }).done(function(str) {
    console.log('Have response: ' + str);
    reload_(opt_afterUrl, opt_timeout);
  });
}

function get(url, opt_data, opt_afterUrl, opt_timeout) {
  request(url, 'GET', opt_data, opt_afterUrl, opt_timeout);
}

function post(url, opt_data, opt_afterUrl, opt_timeout) {
  request(url, 'POST', opt_data, opt_afterUrl, opt_timeout);
}

function openSpecialLink(e) {
  var link = $(this).attr('data-link');
  window.open(link, '_');
  return false;
}

function bindFakeLinks() {
  $('.fake-link').click(openSpecialLink);
}

function markItemDone(key) {
  markItem_(key, 'true');
}

function markItemOpen(key) {
  markItem_(key, 'false');
}

function markItem_(key, done) {
  post('/checklistitem', {
    key: key,
    done: done
  });
}
