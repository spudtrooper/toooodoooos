import helpers
import json
import logging
import os
from google.appengine.api import mail
from google.appengine.api import users
from google.appengine.ext import webapp
from google.appengine.ext.webapp.util import run_wsgi_app
from google.appengine.ext import db
from google.appengine.ext.ndb import msgprop
from google.appengine.ext.webapp import template
from datetime import datetime
from datetime import time
from datetime import timedelta
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

class ListSettings(db.Model):
  list = db.ReferenceProperty(List)
  email_reminder_time = db.TimeProperty()

# ----------------------------------------------------------------------
# Utilities
# ----------------------------------------------------------------------

_APP_NAME = 'toooodoooos'
_SENDER_EMAIL = 'list@toooodoooos.appspotmail.com'

def RenderTemplate(response, name, template_values=None):
  if not template_values:
    template_values = {}
  logging.info('Rendering template[%s] with values[%s]', name, template_values)
  path = os.path.join(os.path.dirname(__file__), 'templates/%s.html' % name)
  response.out.write(template.render(path, template_values))

def RenderTemplateWithOK(response, name, template_values=None):
  logging.info('Rendering with OK template[%s] with values[%s]', 
               name, template_values)
  if not template_values:
    template_values = {}
  path = os.path.join(os.path.dirname(__file__), 'templates/%s.html' % name)
  body = template.render(path, template_values)
  data = {
    'status': 'OK',
    'body': body
  }
  RenderJsonWithOK(response, data)

def RenderJsonWithOK(response, data=None):
  if not data:
    data = {}
  body = {
    'status': 'OK',
    'data': data
  }
  json_data = json.dumps(body)
  response.out.write(json_data)

def ArchiveList(lst):
  logging.info('Archiving list[%s]', lst)
  today = datetime.now().date()
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


def ArchiveUser(user):
  logging.info('Archiving user[%s]', user)
      
  # Add the new ones.
  lists = db.GqlQuery('SELECT * FROM List WHERE author = :1 ORDER BY name', user)
  for lst in lists:
    logging.info('Looking at list for list with name[%s] and key[%s]', lst.name, lst.key())
    ArchiveList(lst)

def CreateEmailContent(list):
    open_items = db.GqlQuery(
      'SELECT * FROM ListItem WHERE list = :1 AND done = false', list)
    done_items = db.GqlQuery(
      'SELECT * FROM ListItem WHERE list = :1 AND done = true', list)

    lines = []
    def Output(s):
      lines.append(str(s))

    open_items = [it for it in open_items]
    done_items = [it for it in done_items]

    Output('List: %s' % (list.name))
    Output('\n')
    if any(open_items):
      Output('Open (%d):' % len(open_items))
      for it in open_items:
        Output(' - %s' % (it.text))
    else:
      Output('No open items')
    Output('\n')
    if any(done_items):
      Output('\nDone (%d):' % len(done_items))
      for it in done_items:
        Output(' - %s' % (it.text))
    else:
      Output('No done items')
    return '\n'.join(lines)

# ----------------------------------------------------------------------
# Handlers
# ----------------------------------------------------------------------

class ArchiveAllHandler(webapp.RequestHandler):
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

class EmailAllHandler(webapp.RequestHandler):
  def get(self):
    author_counts = {}
    list_settingss = db.GqlQuery('SELECT * FROM ListSettings')
    now_hour = self.request.get('now_hour')
    if not now_hour:
      # TODO(jeff): Take into account time zones. Use PST for now.
      now_hour = (datetime.now()  + timedelta(hours=-7)).time().strftime('%H')
    # TODO(jeff): Padding the hour, pad it correctly.
    if len(now_hour) == 1:
      now_hour = '0' + now_hour
    author_counts = {}
    list_settings_count = 0
    logging.info('now_hour: %s', now_hour)
    for list_settings in list_settingss:
      lst = list_settings.list
      list_settings_count += 1
      if lst.author not in author_counts:
        author_counts[lst.author] = 0
      if list_settings.email_reminder_time:
        if list_settings.email_reminder_time.strftime('%H') == now_hour:
          body = CreateEmailContent(lst)
          subject = '[%s] Reminder for list %s' % (_APP_NAME, lst.name)
          recipient_address = lst.author.nickname()
          if '@' not in recipient_address:
            recipient_address += '@gmail.com'
          logging.info('Emailing to recipient_address[%s] body[%s]', recipient_address, body)
          mail.send_mail(sender=_SENDER_EMAIL,
                         to=recipient_address,
                         subject=subject,
                         body=body)
          cnt = author_counts.get(lst.author, 0)
          author_counts[lst.author] = cnt + 1

    author_stats = []
    for author, cnt in author_counts.iteritems():
      author_stats.append({
        'nickname': author.nickname(),
        'count': cnt
      })

    template_values = {
      'author_stats': author_stats,
      'now_hour': now_hour,
      'list_settings_count': list_settings_count,
    }

    RenderTemplate(self.response, 'emailall', template_values)

class ArchiveListHandler(webapp.RequestHandler):
  def post(self):  
    list = db.get(self.request.get('key'))
    ArchiveList(list)
    RenderJsonWithOK(self.response)

class ArchiveHandler(webapp.RequestHandler):
  def post(self):
    user = users.get_current_user()
    if not user:
      return
    ArchiveUser(user)
    RenderJsonWithOK(self.response)

class IndexPageHandler(webapp.RequestHandler):
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

class NewListHandler(webapp.RequestHandler):
  def post(self):
    name = self.request.get('name')
    logging.info('Adding new list with name[%s]', name)
    list = List(author=users.get_current_user(),
                name=name)
    list.put()
    RenderJsonWithOK(self.response)

# Returns an object of the form
# {
#  'list': List,
#  'open_items': List(TODO)
#  'done_items': List(TODO)
# }
def GetListAndItems(list):
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

  return {
    'list': list,
    'open_items': sorted_rendered_open_items,
    'done_items': sorted_rendered_done_items,
  }

class AllPageHandler(webapp.RequestHandler):
  def get(self):
    nickname = ''
    user = users.get_current_user()
    if user:
      nickname = user.nickname()
    else:
      self.redirect(users.create_login_url(self.request.uri))
    lists = db.GqlQuery('SELECT * FROM List WHERE author = :1 ORDER BY name', user)
    list_and_items = []
    for list in lists:
      s = GetListAndItems(list)
      logging.info('done_items: %s', s['done_items'])
      # TODO(jeff): Refactor
      open_items = db.GqlQuery(
        'SELECT * FROM ListItem WHERE list = :1 AND done = false', list)
      priorities = [0, 0, 0, 0, 0]
      num_open = 0
      for it in open_items:
        num_open += 1
        priorities[it.priority] = priorities[it.priority] + 1
      list_properties = {
        'name': helpers.Htmlize(list.name),
        'num_open': num_open,
        'key': list.key(),
        'num_p0': priorities[0],
        'num_p1': priorities[1],
        'num_p2': priorities[2],
        'num_p3': priorities[3],
        'num_p4': priorities[4]
      }
      s.update(list_properties)
      list_and_items.append(s)

    template_values = {
      'is_logged_in': not (not users.get_current_user()),
      'logout_link': users.create_logout_url('/'),
      'list_and_items': list_and_items
    }
    
    RenderTemplate(self.response, 'all', template_values)

class ListPageHandler(webapp.RequestHandler):
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
      'num_open_items': len(sorted_rendered_open_items),
      'num_done_items': len(sorted_rendered_done_items),
      'num_items': len(sorted_rendered_open_items) + len(sorted_rendered_done_items),
    }
    RenderTemplate(self.response, 'list', template_values)

class EmailListHandler(webapp.RequestHandler):
  def post(self):
    user = users.get_current_user()
    if not user:
      return
    list = db.get(self.request.get('key'))
    recipient_address = self.request.get('recipient_address')
    body = CreateEmailContent(list)
    subject = 'A list from %s: %s' % (user.nickname(), list.name)
    logging.info('Emailing to recipient_address[%s] body[%s]', recipient_address, body)
    mail.send_mail(sender=_SENDER_EMAIL,
                   to=recipient_address,
                   subject=subject,
                   body=body)
    RenderJsonWithOK(self.response)

def GetOrCreateListSettings(request):
    list_key = request.get('key')
    list = db.get(list_key)
    q = db.GqlQuery('SELECT * FROM ListSettings WHERE list = :1 LIMIT 1', list)
    results = q.fetch(limit=1)
    logging.info('results=%s %d', results, len(results))
    if not results or not any(results):
      list_settings = ListSettings(list=list)
      list_settings.put()
    else:
      list_settings = results[0]
    return list_settings

class ListSettingsHandler(webapp.RequestHandler):
  def get(self):
    user = users.get_current_user()
    if not user:
      return
    list_settings = GetOrCreateListSettings(self.request)
    logging.info('ListSettings: %s', list_settings)
    data = {
      'email_reminder_time': (list_settings.email_reminder_time.strftime('%H:%M') if
                              list_settings.email_reminder_time else '-1')
    }
    RenderJsonWithOK(self.response, data)

class UpdateListSettingsHandler(webapp.RequestHandler):
  def post(self):
    user = users.get_current_user()
    if not user:
      return
    list_settings = GetOrCreateListSettings(self.request)
    logging.info('ListSettings before: %s', list_settings)

    email_reminder_time = self.request.get('email_reminder_time')
    if email_reminder_time:
      if email_reminder_time == '-1':
        new_email_reminder_time = None
      else:
        new_email_reminder_time = datetime.strptime(email_reminder_time, '%H:%M').time()
      logging.info('New time: %s', new_email_reminder_time)
      list_settings.email_reminder_time = new_email_reminder_time
      list_settings.save()
      
    logging.info('ListSettings after: %s', list_settings.email_reminder_time)
    RenderJsonWithOK(self.response)

class NewListItemHandler(webapp.RequestHandler):
  def post(self):
    list = db.get(self.request.get('list_key'))
    text = self.request.get('text')
    priority = (int(self.request.get('priority')) if self.request.get('priority') else 2)
    item = ListItem(text=text,
                    list=list,
                    priority=priority,
                    done=False)
    logging.info('Adding new list item[%s] from text[%s] priority[%d]',
                 item, text, priority)
    item.put()
    list.save()
    template_values = {
      'item': item
    }
    RenderTemplateWithOK(self.response, '_list_open_item', template_values)

class CheckListItemHandler(webapp.RequestHandler):
  def post(self):
    item = db.get(self.request.get('key'))
    list = db.get(item.list.key())
    logging.info('Have list[%s]',  list)
    done = self.request.get('done') == 'true'
    if done:
      item.done = True
    else:
      item.done = False
    list.save()
    item.date = datetime.now()
    item.put()

    template_values = {
      'item': item
    }
    RenderTemplateWithOK(self.response, 
                         '_list_done_item' if done else '_list_open_item', 
                         template_values)

class DeleteListItemHandler(webapp.RequestHandler):
  def post(self):
    item = db.get(self.request.get('key'))
    list = db.get(item.list)
    logging.info('Deleting %s' % item)
    item.delete()
    RenderJsonWithOK(self.response)

class DeleteListHandler(webapp.RequestHandler):
  def post(self):  
    list = db.get(self.request.get('key'))
    items = db.GqlQuery('SELECT * FROM ListItem WHERE list = :1', list)
    list.delete()
    db.delete(items)
    RenderJsonWithOK(self.response)

class ChangesHandler(webapp.RequestHandler):
  def get(self):
    RenderTemplate(self.response, 'changes')

class HistoryHandler(webapp.RequestHandler):
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
  [('/', IndexPageHandler),
   ('/all', AllPageHandler),
   ('/list', ListPageHandler),
   ('/checklistitem', CheckListItemHandler),
   ('/deletelistitem', DeleteListItemHandler),
   ('/deletelist', DeleteListHandler),
   ('/archive', ArchiveHandler),
   ('/archivelist', ArchiveListHandler),
   ('/history', HistoryHandler),
   ('/changes', ChangesHandler),
   ('/newlist', NewListHandler),
   ('/newlistitem', NewListItemHandler),
   ('/emaillist', EmailListHandler),
   ('/listsettings', ListSettingsHandler),
   ('/updatelistsettings', UpdateListSettingsHandler),
 ], debug=True)

cron = webapp.WSGIApplication(
  [('/archiveall', ArchiveAllHandler),
   ('/emailall', EmailAllHandler)
 ], debug=True)
