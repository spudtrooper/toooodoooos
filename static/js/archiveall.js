function archiveAll(listKey) {
  $.ajax({
    url: '/archiveall',
    data: {
    },
    method: 'GET',
    context: document.body
  }).done(function(str) {
    reload_();
  });
}

function reload_() {
  console.log('reloading...');
  setTimeout(function() {
    console.log('loading page');
    document.location = String(document.location).replace(/#.*/, '');
  }, 200);
}
