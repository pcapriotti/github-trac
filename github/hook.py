# trac-post-commit-hook
# ----------------------------------------------------------------------------
# Copyright (c) 2004 Stephen Hansen 
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to
# deal in the Software without restriction, including without limitation the
# rights to use, copy, modify, merge, publish, distribute, sublicense, and/or
# sell copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
#   The above copyright notice and this permission notice shall be included in
#   all copies or substantial portions of the Software. 
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL
# THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS
# IN THE SOFTWARE.
# ----------------------------------------------------------------------------
#
# It searches commit messages for text in the form of:
#   command #1
#   command #1, #2
#   command #1 & #2 
#   command #1 and #2
#
# Instead of the short-hand syntax "#1", "ticket:1" can be used as well, e.g.:
#   command ticket:1
#   command ticket:1, ticket:2
#   command ticket:1 & ticket:2 
#   command ticket:1 and ticket:2
#
# In addition, the ':' character can be omitted and issue or bug can be used
# instead of ticket.
#
# You can have more then one command in a message. The following commands
# are supported. There is more then one spelling for each command, to make
# this as user-friendly as possible.
#
#   close, closed, closes, fix, fixed, fixes
#     The specified issue numbers are closed with the contents of this
#     commit message being added to it. 
#   references, refs, addresses, re, see 
#     The specified issue numbers are left in their current status, but 
#     the contents of this commit message are added to their notes. 
#
# A fairly complicated example of what you can do is with a commit message
# of:
#
#    Changed blah and foo to do this or that. Fixes #10 and #12, and refs #12.
#
# This will close #10 and #12, and add a note to #12.

import re
import os
import sys
from datetime import datetime

from trac.env import open_environment
from trac.ticket.notification import TicketNotifyEmail
from trac.ticket import Ticket
from trac.ticket.web_ui import TicketModule
# TODO: move grouped_changelog_entries to model.py
from trac.util.text import to_unicode
from trac.util.datefmt import utc
from trac.versioncontrol.api import NoSuchChangeset

ticket_prefix = '(?:#|(?:ticket|issue|bug)[: ]?)'
ticket_reference = ticket_prefix + '[0-9]+'
ticket_command =  (r'(?P<action>[A-Za-z]*).?'
                   '(?P<ticket>%s(?:(?:[, &]*|[ ]?and[ ]?)%s)*)' %
                   (ticket_reference, ticket_reference))
     
command_re = re.compile(ticket_command)
ticket_re = re.compile(ticket_prefix + '([0-9]+)')

class CommitHook:
    _supported_cmds = {'close':      '_cmdClose',
                       'closed':     '_cmdClose',
                       'closes':     '_cmdClose',
                       'fix':        '_cmdClose',
                       'fixed':      '_cmdClose',
                       'fixes':      '_cmdClose',
                       'addresses':  '_cmdRefs',
                       're':         '_cmdRefs',
                       'references': '_cmdRefs',
                       'refs':       '_cmdRefs',
                       'see':        '_cmdRefs'}

    def __init__(self, env):
        self.env = env

    def process(self, commit):
        msg = commit['message']
        author = commit['author']['name']
        timestamp = datetime.now(utc)
        
        cmd_groups = command_re.findall(msg)

        tickets = {}
        for cmd, tkts in cmd_groups:
            funcname = self.__class__._supported_cmds.get(cmd.lower(), '')
            if funcname:
                for tkt_id in ticket_re.findall(tkts):
                    func = getattr(self, funcname)
                    tickets.setdefault(tkt_id, []).append(func)

        for tkt_id, cmds in tickets.iteritems():
            try:
                db = self.env.get_db_cnx()
                
                ticket = Ticket(self.env, int(tkt_id), db)
                for cmd in cmds:
                    cmd(ticket)

                # determine sequence number... 
                cnum = 0
                tm = TicketModule(self.env)
                for change in tm.grouped_changelog_entries(ticket, db):
                    if change['permanent']:
                        cnum += 1
                
                ticket.save_changes(author, msg, timestamp, db, cnum+1)
                db.commit()
                
                tn = TicketNotifyEmail(self.env)
                tn.notify(ticket, newticket=0, modtime=timestamp)
            except Exception, e:
                import traceback
                traceback.print_exc(file=sys.stderr)
                #print>>sys.stderr, 'Unexpected error while processing ticket ' \
                                   #'ID %s: %s' % (tkt_id, e)
            

    def _cmdClose(self, ticket):
        ticket['status'] = 'closed'
        ticket['resolution'] = 'fixed'

    def _cmdRefs(self, ticket):
        pass
