function reload_(opt_url) {
  setTimeout(function() {
    document.location = opt_url ? opt_url : String(document.location).replace(/#.*/, '');
  }, 50);
}

function request(url, method, opt_data, opt_afterUrl) {
  var data = opt_data || {};
  $.ajax({
    url: url,
    data: data,
    method: method,
    context: document.body
  }).done(function(str) {
    console.log('Have response: ' + str);
    reload_(opt_afterUrl);
  });
}

function get(url, opt_data, opt_afterUrl) {
  request(url, 'GET', opt_data, opt_afterUrl);
}

function post(url, opt_data, opt_afterUrl) {
  request(url, 'POST', opt_data, opt_afterUrl);
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
