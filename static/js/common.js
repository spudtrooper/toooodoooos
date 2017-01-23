const _ALERT_TIMEOUT_MILLIS = 2000;
const _DEFAULT_RELOAD_TIMEOUT_MILLIS = 50;

function reload_(opt_url, opt_timeout) {
  setTimeout(function() {
    document.location = opt_url ? opt_url : String(document.location).replace(/#.*/, '');
  }, opt_timeout || _DEFAULT_RELOAD_TIMEOUT_MILLIS);
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

function requestWithCallback(url, method, callback, opt_data, opt_timeout) {
  var data = opt_data || {};
  $.ajax({
    url: url,
    data: data,
    method: method,
    context: document.body
  }).done(function(str) {
    console.log('Have response: ' + str);
    setTimeout(function() {
      callback.call(null, str);
    }, opt_timeout || 50);
  });
}

function getWithCallback(url, callback, opt_data, opt_timeout) {
  requestWithCallback(url, 'GET', callback, opt_data, opt_timeout);
}

function postWithCallback(url, callback, opt_data, opt_timeout) {
  requestWithCallback(url, 'POST', callback, opt_data, opt_timeout);
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

function success(msg) {
  showMessage_(msg, '.success-alert-container');
}

function info(msg) {
  showMessage_(msg, '.info-alert-alert-container');
}

function warn(msg) {
  showMessage_(msg, '.warning-alert-container');
}

function error(msg) {
  showMessage_(msg, '.danger-alert-container');
}

function showMessage_(msg, selector) {
  $(selector).html(msg);
  $(selector).fadeIn();
  setTimeout(function() {
    $(selector).fadeOut();
  }, _ALERT_TIMEOUT_MILLIS);
}

