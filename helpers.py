import re

def Htmlize(s):
  # Since we can't put real A elements inside of A elements with class
  # list-group-item, we'll add fake links.
  #   - stick the link on attribute 'data-link'
  #   - anyone who adds fake links should call bindFakeLinks, e.g.
  #     $(window).load(bindFakeLinks); This will handle clicks with
  #     openSpecialLink
  s = re.sub(r'\b(http|https|go|mdb|cr|cl|g|b)/([\w\-\#]+)', 
             r'<span class="fake-link" data-link="http://\1/\2">\1/\2</span>', 
             s)
  return s
