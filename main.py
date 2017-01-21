import helpers
import logging
import os
from google.appengine.api import users
from google.appengine.ext import webapp
from google.appengine.ext.webapp.util import run_wsgi_app
from google.appengine.ext import db
from google.appengine.ext.ndb import msgprop
from google.appengine.ext.webapp import template
from datetime import datetime
from protorpc import messages

# ----------------------------------------------------------------------
# Model
# ----------------------------------------------------------------------

class List(db.Model):
  author = db.UserProperty()
  name = db.StringProperty(multiline=False)
  date = db.DateTimeProperty(auto_now_add=True)
  num_open = db.IntegerProperty(default=0) # deprecated
  num_done = db.IntegerProperty(default=0) # deprecated

class ListItem(db.Model):
  list = db.ReferenceProperty(List)
  text = db.StringProperty(multiline=False)
  done = db.BooleanProperty()
  date = db.DateTimeProperty(auto_now_add=True)
  priority = db.IntegerProperty(default=2)

class ArchivedList(db.Model):
  archived_list = db.ReferenceProperty(List)
  author = db.UserProperty()
  name = db.StringProperty(multiline=False)
  list_date = db.DateTimeProperty()
  date = db.DateProperty()

class ArchivedListItem(db.Model):
  list_item = db.ReferenceProperty(ListItem)
  archived_list = db.ReferenceProperty(ArchivedList)
  text = db.StringProperty(multiline=False)
  done = db.BooleanProperty()
  item_date = db.DateTimeProperty()
  date = db.DateProperty()

# ----------------------------------------------------------------------
# Utilities
# ----------------------------------------------------------------------


def RenderTemplate(response, name, template_values):
  logging.info('Rendering template[%s] with values[%s]', name, template_values)
  path = os.path.join(os.path.dirname(__file__), 'templates/%s.html' % name)
  response.out.write(template.render(path, template_values))

def ArchiveUser(user):
  logging.info('Archiving user[%s]', user)
  
  today = datetime.now().date()
      
  # Add the new ones.
  lists = db.GqlQuery('SELECT * FROM List WHERE author = :1 ORDER BY name', user)
  for lst in lists:
    logging.info('Looking at list for list with name[%s] and key[%s]', lst.name, lst.key())
    
    # Get or create a new ArchivedList
    archived_lists = db.GqlQuery(
      'SELECT * FROM ArchivedList WHERE archived_list = :1 AND date = :2', 
      lst, today)
    if archived_lists and any(archived_lists):
      logging.info('Using existing archived list for list with name[%s] and key[%s]',
                   lst.name, lst.key())
      archived_list = archived_lists[0]
    else:
      logging.info('Creating a new archived list for list with name[%s] and key[%s]',
                   lst.name, lst.key())
      archived_list = ArchivedList(author=lst.author,
                                   archived_list=lst,
                                   name=lst.name,
                                   date=today,
                                   list_date=lst.date)
      archived_list.put()
    items = db.GqlQuery('SELECT * FROM ListItem WHERE list = :1', lst)
    for it in items:
      # Delete all the existing archived items for this item.
      archived_list_items = db.GqlQuery(
        ('SELECT * FROM ArchivedListItem WHERE list_item = :1 AND '
         'archived_list = :2 AND date = :3'), 
        it, archived_list, today)
      if archived_list_items and any(archived_list_items):
        for archived_list_item in archived_list_items:
          logging.info('Found an item already key[%s] text[%s], will delete it',
                       it.key(), it.text)
          archived_list_item.delete()
      new_item = ArchivedListItem(text=it.text,
                                  list_item=it,
                                  archived_list=archived_list,
                                  done=it.done,
                                  date=today,
                                  item_date=it.date)
      new_item.put()

      if it.done:
        logging.info('Marking item done for item[%s] in list[%s]', it.text, lst.name)
        # If this item is done remove it from the list.
        it.delete()
      else:
        new_item.put()
    lst.save()

# ----------------------------------------------------------------------
# Handlers
# ----------------------------------------------------------------------

class ArchiveAll(webapp.RequestHandler):
  def get(self):
    author_counts = {}
    lists = db.GqlQuery('SELECT * FROM List')
    for lst in lists:
      cnt = author_counts.get(lst.author, 0)
      author_counts[lst.author] = cnt + 1
    logging.info('author_counts: %s', author_counts)

    # Do the archive.
    for u in author_counts.keys():
      ArchiveUser(u)

    author_stats = []
    for author, cnt in author_counts.iteritems():
      author_stats.append({
        'nickname': author.nickname(),
        'count': cnt
      })

    template_values = {
      'author_stats': author_stats
    }

    RenderTemplate(self.response, 'archiveall', template_values)

class Archive(webapp.RequestHandler):
  def post(self):
    user = users.get_current_user()
    if not user:
      return
    ArchiveUser(user)
    self.response.out.write('OK')

class IndexPage(webapp.RequestHandler):
  def get(self):
    nickname = ''
    user = users.get_current_user()
    if user:
      nickname = user.nickname()
    else:
      self.redirect(users.create_login_url(self.request.uri))
    lists = db.GqlQuery('SELECT * FROM List WHERE author = :1 ORDER BY name', user)

    rendered_lists = []
    for lst in lists:
      open_items = db.GqlQuery(
        'SELECT * FROM ListItem WHERE list = :1 AND done = false', lst)
      priorities = [0, 0, 0, 0, 0]
      num_open = 0
      for it in open_items:
        num_open += 1
        priorities[it.priority] = priorities[it.priority] + 1
      rendered_lists.append({
        'name': helpers.Htmlize(lst.name),
        'num_open': num_open,
        'key': lst.key(),
        'num_p0': priorities[0],
        'num_p1': priorities[1],
        'num_p2': priorities[2],
        'num_p3': priorities[3],
        'num_p4': priorities[4]
      })
      
    template_values = {
      'is_logged_in': not (not users.get_current_user()),
      'nickname': nickname,
      'logout_link': users.create_logout_url('/'),
      'lists': rendered_lists,
    }
    
    RenderTemplate(self.response, 'index', template_values)

class NewList(webapp.RequestHandler):
  def post(self):
    name = self.request.get('name')
    logging.info('Adding new list with name[%s]', name)
    list = List(author=users.get_current_user(),
                name=name)
    list.put()
    self.response.out.write('OK')

class ListPage(webapp.RequestHandler):
  def get(self):
    list = db.get(self.request.get('key'))
    open_items = db.GqlQuery(
      'SELECT * FROM ListItem WHERE list = :1 AND done = false', list)
    done_items = db.GqlQuery(
      'SELECT * FROM ListItem WHERE list = :1 AND done = true', list)

    rendered_open_items = []
    rendered_done_items = []
    for it in open_items:
      rendered_open_items.append({
        'text': helpers.Htmlize(it.text),
        'key': it.key(),
        'priority': it.priority
      })
    for it in done_items:
      rendered_done_items.append({
        'text': helpers.Htmlize(it.text),
        'key': it.key(),
        'priority': it.priority,
        'date': it.date
      })

    # Sort open items by priority.
    sorted_rendered_open_items = sorted(rendered_open_items, key=lambda it: it['priority'])

    # Sort done items by date.
    sorted_rendered_done_items = sorted(rendered_done_items, key=lambda it: it['date'])

    template_values = {
      'list': list,
      'open_items': sorted_rendered_open_items,
      'done_items': sorted_rendered_done_items,
    }
    RenderTemplate(self.response, 'list', template_values)

class NewListItem(webapp.RequestHandler):
  def post(self):
    list = db.get(self.request.get('list_key'))
    text = self.request.get('text')
    priority = int(self.request.get('priority'))
    item = ListItem(text=text,
                    list=list,
                    priority=priority,
                    done=False)
    logging.info('Adding new list item[%s] from text[%s] priority[%d]',
                 item, text, priority)
    item.put()
    list.save()
    self.response.out.write('OK')

class CheckListItem(webapp.RequestHandler):
  def post(self):
    item = db.get(self.request.get('key'))
    list = db.get(item.list.key())
    logging.info('Have list[%s]',  list)
    if (self.request.get('done') == 'true'):
      item.done = True
    else:
      item.done = False
    list.save()
    item.date = datetime.now()
    item.put()

    self.response.out.write('OK')

class DeleteListItem(webapp.RequestHandler):
  def post(self):
    item = db.get(self.request.get('key'))
    list = db.get(item.list)
    logging.info('Deleting %s' % item)
    item.delete()
    self.response.out.write('OK')

class DeleteList(webapp.RequestHandler):
  def post(self):  
    list = db.get(self.request.get('key'))
    items = db.GqlQuery('SELECT * FROM ListItem WHERE list = :1', list)
    list.delete()
    db.delete(items)
    self.response.out.write('OK')

class History(webapp.RequestHandler):
  def get(self):
    user = users.get_current_user()
    if not user:
      return

    archived_lists = db.GqlQuery(
      'SELECT * FROM ArchivedList WHERE author = :1 ORDER BY date DESC', user)

    # Maps dates to lists of ListItem for that date
    # date ->
    #  archived_list -> [archived_list_item]
    dates_to_list_map = {}
    for lst in archived_lists:
      archived_list_map = dates_to_list_map.get(lst.date)
      if not archived_list_map:
        archived_list_map = {}
        dates_to_list_map[lst.date] = archived_list_map
      items = db.GqlQuery('SELECT * FROM ArchivedListItem WHERE archived_list = :1', lst)
      archived_list_items = []
      for it in items:
        archived_list_items.append(it)
      archived_list_map[lst] = archived_list_items
    logging.info('dates_to_list_map: %s' % dates_to_list_map)

    stats = {}
    for date, archived_list_map in dates_to_list_map.iteritems():
      stat = {}
      stats[date] = stat
      archived_lists_objs = []
      for archived_list, archived_list_items in archived_list_map.iteritems():
        archived_list_obj = {}
        archived_lists_objs.append(archived_list_obj)
        archived_list_obj['name'] = archived_list.name
        open_items = []
        done_items = []
        for it in archived_list_items:
          if it.done:
            done_items.append(it)
          else:
            open_items.append(it)
        archived_list_obj['open_items'] = open_items
        archived_list_obj['done_items'] = done_items
      stat['archived_lists'] = archived_lists_objs
      
    sorted_stats = []
    dates = stats.keys()
    dates.sort(reverse=True)
    for d in dates:
      sorted_stats.append({
        'date': d,
        'stat': stats[d]})

    logging.info('stats: %s' % sorted_stats)
    template_values = {
      'stats': sorted_stats
    }
    
    RenderTemplate(self.response, 'history', template_values)

app = webapp.WSGIApplication(
  [('/', IndexPage),
   ('/list', ListPage),
   ('/checklistitem', CheckListItem),
   ('/deletelistitem', DeleteListItem),
   ('/deletelist', DeleteList),
   ('/archive', Archive),
   ('/history', History),
   ('/newlist', NewList),
   ('/newlistitem', NewListItem)
 ], debug=True)

cron = webapp.WSGIApplication(
  [('/archiveall', ArchiveAll)
 ], debug=True)
