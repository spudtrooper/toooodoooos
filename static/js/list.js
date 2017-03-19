function deleteList(listKey, name) {
  var ans = confirm('Are you sure you want to delete "' + name + '"?');
  if (ans) {
    post('/deletelist', {key: listKey}, '/');
  }
}

function archiveList(listKey) {
  post('/archivelist', {key: listKey});
}

function emailList(listKey) {
  var recipientAddress = prompt('Recipient\'s address:')
  if (!recipientAddress) {
    warn('No recipient address');
    return;
  }
  postWithCallback(
    '/emaillist', 
    function(str) {
      if (str == 'OK') {
        success('Sent to: ' + recipientAddress);
      } else {
        warn('Couldn\'t send to: ' + recipientAddress);
      }
    },
    {key: listKey, recipient_address: recipientAddress});
}

function deleteItem(itemKey) {
  post('/deletelistitem', {key: itemKey});
}

function addNewItem(listKey) {
  var text = $('#text_' + listKey).val();
  if (!text) {
    alert('No text');
    return;
  }

  // Speculatively add the new item.
  $('#text_' + listKey).val('');
  updateNumItems(true, 1);
  
  var onSuccess = function(obj) {
    $('#open-items').append($(obj.body));
    sortAllItems();
  }
  var onFailure = function(obj) {
    // If the request fails, remove the item.
    $('#_item-' + listKey).remove();
    updateNumItems(true, -1);
    sortAllItems();
  };
  postWithCallbacks('/newlistitem', onSuccess, onFailure, {
    list_key: listKey,
    text: text,
  });
}

function addEmailReminderOptions() {
  $('#email-reminder-select').empty();
  var option = $('<option>').text('Never').val(-1);
  $('#email-reminder-select').append(option);
  for (var hr = 0; hr < 24; hr++) {
    var s = String(hr);
    if (s.length < 2) {
      s = '0' + s;
    }
    s += ':00';
    var option = $('<option>').text(s).val(s);
    $('#email-reminder-select').append(option);
  }
}

function updateListSettings() {
  var val = $('#email-reminder-select').val();
  if (!val || val == 'Never') {
    return;
  }
  postWithCallback('/updatelistsettings', sucessWithMsg('Updated email time to ' + val), {
    key: getListKey(),
    email_reminder_time: val,
  });
}

function initListSettings(listKey) {
  var onSuccess = function(objStr) {
    var obj = JSON.parse(objStr);
    var data = obj['data'];
    var t = data['email_reminder_time'];
    if (t) {
      $('#email-reminder-select').val(t);
      $('.selectpicker').selectpicker('refresh');
    }
  };
  getWithCallback('/listsettings', onSuccess, {
    key: listKey,
  });
  $('#email-reminder-select').change(updateListSettings);
}

function getListKey() {
  return $('#add-form').attr('data-list-key');
}

$(document).ready(function() {
  var listKey = $('#add-form').attr('data-list-key');
  addEmailReminderOptions();
  $('.selectpicker').selectpicker();
  $('#add-form').submit(function(e){
    e.preventDefault();
    addNewItem(listKey);
  });
  sortAllItems();
  initListSettings(listKey);
});
