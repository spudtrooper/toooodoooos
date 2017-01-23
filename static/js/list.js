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

function priorityStringToInt(s) {
  return parseInt(s.replace(/^P/, ''));
}

function addNewItem(listKey) {
  var text = $('#text_' + listKey).val();
  if (!text) {
    alert('No text');
    return;
  }
  var priority = priorityStringToInt($('#priority_' + listKey).val());
  post('/newlistitem', {
    list_key: listKey,
    text: text,
    priority: priority
  });
}

$(document).ready(function() {
  $('.selectpicker').selectpicker();
});
