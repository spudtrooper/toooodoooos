function archive(listKey) {
  post('/archive');
}

function addNewList() {
  var name = $('#new-list-name-text').val();
  if (!name) {
    alert('No name');
    return;
  }
  post('/newlist', {name: name}, undefined, 200);
}

function deleteList(listKey) {
  post('/deletelist', {key: listKey});
}
