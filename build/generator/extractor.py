#
# extractor.py: extract function names from declarations in header files
#
# ====================================================================
# Copyright (c) 2000-2003 CollabNet.  All rights reserved.
#
# This software is licensed as described in the file COPYING, which
# you should have received as part of this distribution.  The terms
# are also available at http://subversion.tigris.org/license-1.html.
# If newer versions of this license are posted there, you may use a
# newer version instead, at your option.
#
# This software consists of voluntary contributions made by many
# individuals.  For exact contribution history, see the revision
# history and logs, available at http://subversion.tigris.org/.
# ====================================================================
#

import re
import string


#
# This parses the following two types of declarations:
#
#    void
#    svn_foo_bar (args)
# or
#    void svn_foo_bar (args)
#
# The space is optional, as some of our headers (currently) omit the
# space before the open parenthesis.
#
_funcs = re.compile('^(?:(svn_[a-z_0-9]+)|[a-z].*?(svn_[a-z_0-9]+)) ?\(')

def extract_funcs(fname):
  funcs = [ ]
  for line in open(fname).readlines():
    match = _funcs.match(line)
    if match:
      name = match.group(1) or match.group(2)
      if not name:
        print 'WTF?', match.groups()
      elif name not in _filter_names:
        funcs.append(name)
  return funcs

_filter_names = [
  'svn_boolean_t',  # svn_config_enumerator_t looks like (to our regex) a
                    # function declaration for svn_boolean_t
  ]

if __name__ == '__main__':
  # run the extractor over each file mentioned
  import sys
  for fname in sys.argv[1:]:
    funcs = extract_funcs(fname)
    if funcs:
      print string.join(funcs, '\n')
