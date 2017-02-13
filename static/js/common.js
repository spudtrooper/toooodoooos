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

/**
 * Creates a callback that consumes a JSON string with a 'status'
 * field and calls {@code onSuccess} when status == 'OK', otherwise
 * calls {@code opt_onFailure} if this function is defined.
 * @param {function(!Object)=} opt_onSuccess
 * @param {function(!Object)=} opt_onFailure
 * @return {function(string)}
 */
function createCallbacksFromCallbacks(opt_onSuccess, opt_onFailure) {
  var callback = function(str) {
    var obj = JSON.parse(str);
    console.log('Response: ' + str);
    if (obj.status == 'OK') {
      if (opt_onSuccess) {
        opt_onSuccess.call(null, obj);
      }
    } else {
      if (opt_onFailure) {
        opt_onFailure.call(null, obj);
      }
    }
  };
  return callback;
}

function postWithCallbacks(url, opt_onSuccess, opt_onFailure, opt_data, opt_timeout) {
  requestWithCallback(url, 'POST', 
                      createCallbacksFromCallbacks(opt_onSuccess, opt_onFailure), 
                      opt_data, opt_timeout);
}

function openSpecialLink(e) {
  var link = $(this).attr('data-link');
  window.open(link, '_');
  return false;
}

function bindFakeLinks() {
  $('.fake-link').click(openSpecialLink);
}

function markItemDone(key, el) {
  return markItem_(key, true, el);
}

function markItemOpen(key, el) {
  return markItem_(key, false, el);
}

function updateNumItems(isDone, delta) {
  var id = isDone ? '#num-done-items' : '#num-open-items';
  var cur = parseInt($(id).text());
  $(id).text(cur + delta);
}

function markItem_(key, isDone, el) {
  $(el).remove();

  // Spectutively add the new item.
  updateNumItems(true,  isDone ? +1 : -1);
  updateNumItems(false, isDone ? -1 : +1);

  var onSuccess = function(obj) {
    $(isDone ? '#done-items' : '#open-items').append($(obj.body));
  }
  var onFailure = function(obj) {
    // If the request fails, remove the item.
    $((isDone ? '#done' : '#open') + '-item-' + key).remove();
    $(isDone ? '#open-items' : '#done-items').append($(el));
    updateNumItems(true,  isDone ? -1 : +1);
    updateNumItems(false, isDone ? +1 : -1);
  };
  postWithCallbacks('/checklistitem', onSuccess, onFailure, {
    key: key,
    done: String(isDone)
  });
  return false;
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

