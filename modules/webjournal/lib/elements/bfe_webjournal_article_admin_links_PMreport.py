#!/usr/bin/env python
# -*- coding: utf-8 -*-
## This file is part of CDS Invenio.
## Copyright (C) 2002, 2003, 2004, 2005, 2006, 2007 CERN.
##
## CDS Invenio is free software; you can redistribute it and/or
## modify it under the terms of the GNU General Public License as
## published by the Free Software Foundation; either version 2 of the
## License, or (at your option) any later version.
##
## CDS Invenio is distributed in the hope that it will be useful, but
## WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
## General Public License for more details.
##
## You should have received a copy of the GNU General Public License
## along with CDS Invenio; if not, write to the Free Software Foundation, Inc.,
## 59 Temple Place, Suite 330, Boston, MA 02111-1307, USA.
"""
WebJournal Element - Display admin links
"""
from invenio.config import \
     CFG_SITE_URL, \
     CFG_SITE_NAME, \
     CFG_SITE_NAME_INTL
from invenio.access_control_engine import acc_authorize_action
from invenio.webjournal_utils import \
     parse_url_string, \
     get_journal_submission_params, \
     get_xml_from_config, \
     get_all_released_issues

def format(bfo):
    """
    Display administration links for this articles when user is an
    editor of the journal
    """
    out = ''
    if bfo.user_info['uri'].startswith('/journal'):
        # Print editing links
        args = parse_url_string(bfo.user_info['uri'])
        journal_name = args["journal_name"]
        category = args["category"]
        editor = False
        if acc_authorize_action(bfo.user_info['uid'], 'cfgwebjournal',
                                name="%s" % journal_name)[0] == 0:
            editor = True
        issue_number = args["issue"]

        if editor:
            recid = bfo.control_field('001')
            (doctype, identifier_element, identifier_field) = \
                      get_journal_submission_params(journal_name)
            if identifier_field.startswith('00'):
                identifier = bfo.control_field(identifier_field)
            else:
                identifier = bfo.field(identifier_field)

            #Figure out what category the article being edited is
            combo_value = ""
            categories = get_xml_from_config(["controller/categories"], journal_name)['controller/categories'][0].split(',')
            for pair in categories:
                name = pair.split('=')[0]
                value = pair.split('=')[1]
                if name.lower() == category.lower():
                    combo_value = value
                    break
            # Do not display the edit links for issues already released
            released_issues = get_all_released_issues( journal_name )
            this_issue_number = args["issue"]
            released = False
            edit_link = """  <p>
    <a href="%(CFG_SITE_URL)s/submit/direct?%(identifier_element)s=%(identifier)s&amp;sub=MBI%(doctype)s&amp;combo%(doctype)s=%(comboValue)s" target="_blank"> >> edit article</a>
  </p>""" %  {'CFG_SITE_URL': CFG_SITE_URL, 'identifier_element': identifier_element,'identifier': identifier,'doctype': doctype, 'comboValue': combo_value }
            if this_issue_number in released_issues:
                edit_link = ""
            out += '''
<div style="float:right;margin-left:5px;font-weight:700;">
  %(edit_link)s
  <p>
    <a href="%(CFG_SITE_URL)s/record/%(recid)s" target="_blank"> >> record in %(CFG_SITE_NAME_INTL)s</a>
  </p>
  <p>
    <a href="%(CFG_SITE_URL)s/admin/webjournal/webjournaladmin.py/regenerate?journal_name=%(journal_name)s&amp;issue=%(issue_number)s"> >> publish changes</a>
  </p>
</div>''' % {'edit_link': edit_link,
             'CFG_SITE_URL': CFG_SITE_URL,
             'comboValue': combo_value,
             'identifier': identifier,
             'recid': recid,
             'journal_name': journal_name,
             'issue_number': issue_number,
             'doctype': doctype,
             'identifier_element': identifier_element,
             'CFG_SITE_NAME_INTL': CFG_SITE_NAME_INTL.get(bfo.lang,
                                                          CFG_SITE_NAME)}



    return out

def escape_values(bfo):
    """
    Called by BibFormat in order to check if output of this element
    should be escaped.
    """
    return 0
