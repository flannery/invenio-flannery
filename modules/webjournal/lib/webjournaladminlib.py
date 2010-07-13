## This file is part of CDS Invenio.
## Copyright (C) 2002, 2003, 2004, 2005, 2006, 2007, 2008 CERN.
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
# pylint: disable-msg=C0301
"""CDS Invenio WebJournal Administration Interface."""

__revision__ = "$Id$"

import sys
import cPickle
import re
import os
from urllib2 import urlopen
from xml.dom import minidom

if sys.hexversion < 0x2040000:
    # pylint: disable-msg=W0622
    from sets import Set as set
    # pylint: enable-msg=W0622

from invenio.errorlib import register_exception
from invenio.config import \
     CFG_SITE_URL, \
     CFG_SITE_LANG, \
     CFG_SITE_NAME, \
     CFG_ETCDIR, \
     CFG_CACHEDIR, \
     CFG_TMPDIR, \
     CFG_SITE_SUPPORT_EMAIL, \
     CFG_BINDIR, \
     CFG_WEBDIR
from invenio.messages import gettext_set_language
from invenio.mailutils import send_email
from invenio.access_control_engine import acc_authorize_action
from invenio.webjournal_config import \
     InvenioWebJournalJournalIdNotFoundDBError, \
     InvenioWebJournalReleaseUpdateError, \
     InvenioWebJournalNoJournalOnServerError
from invenio.webjournal_utils import \
     get_journals_ids_and_names, \
     guess_journal_name, \
     get_current_issue, \
     get_issue_number_display, \
     get_featured_records, \
     add_featured_record, \
     remove_featured_record, \
     clear_cache_for_issue, \
     get_next_journal_issues, \
     get_release_datetime, \
     get_journal_id, \
     compare_issues, \
     get_journal_info_path, \
     get_journal_css_url, \
     get_journal_alert_sender_email, \
     get_journal_alert_recipient_email, \
     get_journal_draft_keyword_to_remove, \
     get_journal_categories, \
     get_journal_articles, \
     get_grouped_issues, \
     get_journal_issue_grouping, \
     get_journal_languages, \
     get_xml_from_config
from invenio.dbquery import run_sql
from invenio.bibrecord import \
     create_record, \
     print_rec
from invenio.bibformat import format_record
from invenio.bibtask import task_low_level_submission
from invenio.webjournal_config import \
     InvenioWebJournalNoJournalOnServerError
from invenio.search_engine import search_pattern
import invenio.template

wjt = invenio.template.load('webjournal')

def getnavtrail(previous = ''):
    """Get the navtrail"""

    navtrail = """<a class="navtrail" href="%s/help/admin">Admin Area</a> """ % (CFG_SITE_URL,)
    navtrail = navtrail + previous
    return navtrail

def make_journal_pdfs( journal_name, journal_issue ):
    """
    Generates a set of PDFs of the index pages and articles for a given journal name and issue

    Parameters:
        journal_name - the string name of the journal to generate the PDFs for
        journal_issue - the string of the issue to generate PDFs for, of the form "02/2009"
            This is because of the way the URLs are put together to create the articles. 
    """
    for issue in journal_issue:
        journal_month = issue.split('/')[0]
        journal_year = issue.split('/')[1]
        #First get a list of the journal categories
        categories = get_journal_categories( journal_name, issue )
        #The following code should not execute if the journal name returns no categories.... This should in theory prevent random strings from being executed....
        for category in categories:
            command_category = CFG_BINDIR + "/wkhtmltopdf  '" + CFG_SITE_URL + '/journal/' + journal_name + '/' + journal_year + '/' + journal_month + '/' + category + "' " + CFG_WEBDIR + "/img/webjournal_archive/" + journal_name + '_' + journal_year + '_' + journal_month + '_' + category + ".pdf" 
#            err, out = commands.getstatusoutput( command_category )
#            if err:
#                raise StandardError, '%s: %s \n %s' % (err, out, command_category)
            command_category = "wget --base=" + CFG_SITE_URL + " -O " + CFG_WEBDIR + "/img/webjournal_archive/" + journal_name + '_' + journal_year + '_' + journal_month + '_' + category + ".html " + CFG_SITE_URL + '/journal/' + journal_name + '/' + journal_year + '/' + journal_month + '/' + category 
#            err, out = commands.getstatusoutput( command_category )
#            if err:
#                raise StandardError, '%s: %s \n %s' % (err, out, command_category)

            #Now get a list of all articles in that category
            articles = get_journal_articles( journal_name, issue, category )
            for article_group in articles:
                for article in articles[article_group]:
                    command_article = CFG_BINDIR + "/wkhtmltopdf  '" + CFG_SITE_URL + '/journal/' + journal_name + '/' + journal_year + '/' + journal_month + '/' + category + '/' + str(article) + "' " + CFG_WEBDIR + "/img/webjournal_archive/" + journal_name + '_' + journal_year + '_' + journal_month + '_' + category + '_' + str(article) + '.pdf' 
#                    err, out = commands.getstatusoutput( command_article )
#                    if err:
#                        raise StandardError, '%s: %s \n %s' % (err, out, command_article)
                    command_article = "wget --base=" + CFG_SITE_URL + " -O " + CFG_WEBDIR + "/img/webjournal_archive/" + journal_name + '_' + journal_year + '_' + journal_month + '_' + category + '_' + str(article) + ".html " + CFG_SITE_URL + '/journal/' + journal_name + '/' + journal_year + '/' + journal_month + '/' + category + '/' + str(article)
#                    err, out = commands.getstatusoutput( command_article )
#                    if err:
#                        raise StandardError, '%s: %s \n %s' % (err, out, command_article)

def perform_index(ln=CFG_SITE_LANG, journal_name=None, action=None, uid=None):
    """
    Index page

    Lists the journals, and offers options to edit them, delete them
    or add new journal.

    Parameters:
        journal_name  -  the journal affected by action, if any
              action  -  one of ['', 'askDelete', _('Delete'), _('Cancel')]
                  ln  -  language
                 uid  -  user id
    """
    _ = gettext_set_language(ln)

    msg = None
    if action == 'askDelete' and journal_name is not None:
        msg = '''<fieldset style="display:inline;margin-left:auto;margin-right:auto;">
        <legend>Delete Journal Configuration</legend><span style="color:#f00">Are you sure you want to delete the configuration of %(journal_name)s?
        <form action="%(CFG_SITE_URL)s/admin/webjournal/webjournaladmin.py">
        <input type="hidden" name="journal_name" value="%(journal_name)s" />
        <input class="formbutton" type="submit" name="action" value="%(delete)s" />
        <input class="formbutton" type="submit" name="action" value="%(cancel)s" />
        </form></span></fieldset>''' % {'CFG_SITE_URL': CFG_SITE_URL,
                                        'journal_name': journal_name,
                                        'delete': _("Delete"),
                                        'cancel': _("Cancel")}

    if action == _("Delete") and journal_name is not None:
        # User confirmed and clicked on "Delete" button
        remove_journal(journal_name)

    journals = get_journals_ids_and_names()
    # Only keep journal that user can view or edit
    journals = [(journal_info, acc_authorize_action(uid,
                                                    'cfgwebjournal',
                                                    name=journal_info['journal_name'],
                                                    with_editor_rights='yes')[0] == 0) \
                 for journal_info in journals \
                 if acc_authorize_action(uid,
                                         'cfgwebjournal',
                                         name=journal_info['journal_name'])[0] == 0]
    return wjt.tmpl_admin_index(ln=ln,
                                journals=journals,
                                msg=msg)

def perform_administrate(ln=CFG_SITE_LANG, journal_name=None,
                         as_editor=True):
    """
    Administration of a journal

    Show the current and next issues/publications, and display links
    to more specific administrative pages.

    Parameters:
        journal_name  -  the journal to be administrated
                  ln  -  language
        with_editor_rights  -  True if can edit configuration. Read-only mode otherwise
    """
    if journal_name is None:
        try:
            journal_name = guess_journal_name(ln)
        except InvenioWebJournalNoJournalOnServerError, e:
            return e.user_box()

    if not can_read_xml_config(journal_name):
        return '<span style="color:#f00">Configuration could not be read. Please check that %s/webjournal/%s/%s-config.xml exists and can be read by the server.</span><br/>' % (CFG_ETCDIR, journal_name, journal_name)

    current_issue = get_current_issue(ln, journal_name)
    current_publication = get_issue_number_display(current_issue,
                                                   journal_name,
                                                   ln)
    issue_list = get_grouped_issues(journal_name, current_issue)
    next_issue_number = get_next_journal_issues(issue_list[-1], journal_name, 1)

    return wjt.tmpl_admin_administrate(journal_name,
                                       current_issue,
                                       current_publication,
                                       issue_list,
                                       next_issue_number[0],
                                       ln,
                                       as_editor=as_editor)

def perform_feature_record(journal_name,
                           recid,
                           img_url='',
                           action='',
                           ln=CFG_SITE_LANG):
    """
    Interface to feature a record

    Used to list, add and remove featured records of the journal.

    Parameters:
        journal_name  -  the journal for which the article is featured
               recid  -  the record affected by 'action'
             img_url  -  the URL to image displayed with given record
                         (only when action == 'add')
              action  -  One of ['', 'add', 'askremove', _('Remove'), _('Cancel')]
                  ln  -  language
    """
    _ = gettext_set_language(ln)

    if action == 'add':
        result = add_featured_record(journal_name, recid, img_url)
        if result == 0:
            msg ='''<span style="color:#0f0">Successfully featured
            <a href="%(CFG_SITE_URL)s/record/%(recid)s">record %(recid)s</a>.
        Go to the <a href="%(CFG_SITE_URL)s/journal/%(name)s">%(name)s journal</a> to
        see the result.</span>''' % {'CFG_SITE_URL': CFG_SITE_URL,
                                  'name': journal_name,
                                  'recid': recid}
        elif result == 1:
            msg = '''<span style="color:#f00"><a href="%(CFG_SITE_URL)s/record/%(recid)s">record %(recid)s</a> is already featured. Choose another one or remove it first.</span>''' % \
                  {'CFG_SITE_URL': CFG_SITE_URL,
                   'recid': recid}
        else:
            msg = '''<span style="color:#f00">Record could not be featured. Check file permission.</span>'''

        featured_records = get_featured_records(journal_name)
        return wjt.tmpl_admin_feature_record(ln=ln,
                                             journal_name=journal_name,
                                             featured_records=featured_records,
                                             msg=msg)
    elif action == 'askremove':
        msg = '''<fieldset style="display:inline;margin-left:auto;margin-right:auto;">
        <legend>Remove featured record</legend><span style="color:#f00">Are you sure you want to remove <a href="%(CFG_SITE_URL)s/record/%(recid)s">record %(recid)s</a> from the list of featured record?
        <form action="%(CFG_SITE_URL)s/admin/webjournal/webjournaladmin.py/feature_record">
        <input type="hidden" name="journal_name" value="%(name)s" />
        <input type="hidden" name="recid" value="%(recid)s" />
        <input class="formbutton" type="submit" name="action" value="%(remove)s" />
        <input class="formbutton" type="submit" name="action" value="%(cancel)s" />
        </form></span></fieldset>''' % \
            {'CFG_SITE_URL': CFG_SITE_URL,
             'name': journal_name,
             'recid': recid,
             'cancel': _("Cancel"),
             'remove': _("Remove")}
        featured_records = get_featured_records(journal_name)
        return wjt.tmpl_admin_feature_record(ln=ln,
                                             journal_name=journal_name,
                                             featured_records=featured_records,
                                             msg=msg)
    elif action == _("Remove"):
        result = remove_featured_record(journal_name, recid)
        msg = '''<span style="color:#f00"><a href="%(CFG_SITE_URL)s/record/%(recid)s">Record %(recid)s</a>
        has been removed.</span>''' % \
            {'CFG_SITE_URL': CFG_SITE_URL,
             'recid': recid}
        featured_records = get_featured_records(journal_name)
        return wjt.tmpl_admin_feature_record(ln=ln,
                                             journal_name=journal_name,
                                             featured_records=featured_records,
                                             msg=msg)
    else:
        msg = '''Here you can choose which records from the %s should
        be featured on the journal webpage.''' % CFG_SITE_NAME
        featured_records = get_featured_records(journal_name)
        return wjt.tmpl_admin_feature_record(ln=ln,
                                             journal_name=journal_name,
                                             featured_records=featured_records,
                                             msg=msg)
def perform_regenerate_issue(issue,
                             journal_name,
                             ln=CFG_SITE_LANG):
    """
    Clears the cache for the given issue.

    Parameters:
        journal_name  -  the journal for which the cache should be
                         deleted
               issue  -  the issue for which the cache should be deleted
                  ln  -  language
    """
    success = clear_cache_for_issue(journal_name,
                                    issue)
    if success:
        return wjt.tmpl_admin_regenerate_success(ln,
                                                 journal_name,
                                                 issue)
    else:
        return wjt.tmpl_admin_regenerate_error(ln,
                                               journal_name,
                                               issue)

def perform_regenerate_meetings(issue,
                             journal_name,
                             ln=CFG_SITE_LANG):
    """
    This function will generate the XML record for the given journal issue
    if one is not present, it will create one and insert it.  
    If one (or more) already exists, it will replace the first XML 
    record found with new data obtained from the Indico server 
    specified in the journal XML configuration file. 
    """ 
    indico_url = get_xml_from_config(["controller/meetings/indico_url"], journal_name)['controller/meetings/indico_url'][0]
    indico_categories = get_xml_from_config(["controller/meetings/indico_categories"], journal_name)['controller/meetings/indico_categories'][0]
    display_num_meetings = get_xml_from_config(["controller/meetings/display_num_meetings"], journal_name)['controller/meetings/display_num_meetings'][0]
    xml_doc_type = get_xml_from_config(["controller/meetings/record_type"], journal_name)['controller/meetings/record_type'][0]

    xml_records = search_pattern(p='773__t:%s and 773__n:%s and 980__a:%s not 980__c:DELETED' % (journal_name, issue, xml_doc_type ) ).tolist()
    control_field = ""
    recid = 0
    if len(xml_records) > 0:
        control_field = '<controlfield tag="001">%i</controlfield>' % xml_records[0] 
        recid = xml_records[0]
        
    """
    Need to add in some code here to delete the previous records or at least set them up to be replaced....
    """
    dates = issue.split("/")
    the_day = str(1)
    the_month = str(int(dates[0]) - 1)
    the_year = str(dates[1])
    if the_month == str(0):
        the_month = str(12)
        the_year = str( int(the_year) - 1 )
    indico_url = indico_url.replace( "THE_DATE", the_year + "-" + the_month + "-" + the_day )
    """
    Also would like to decide on behavior for the temp file...
    Python's built in temp file library is one option, 
    or keep with the convention of using the var temp directory
    """

    meeting_xml_entries = []
    # Lets embed the category title in the XML file for the JavaScript editor. 
    # For displaying it on the journal, we will styll grab the value from the configuration
    # just in case it has changed
    indico_category_names = get_xml_from_config(["controller/meetings/indico_category_names"], journal_name)['controller/meetings/indico_category_names'][0].split(';')
    category_names = {}
    for pair in indico_category_names:
        category_names[pair.split('=')[0]] = pair.split('=')[1]

    for category in indico_categories.split(","):
        """ string is deprecated, but I am using it as a solution for the time being...."""
        category_url = indico_url.replace( "CATEGORY", category )
        try:
            xml_from_indico = urlopen( category_url )
        except:
            meeting_xml_entries.append( [ "Error connectiong to %s" % category_url ] )
            continue
        xml_dom = minidom.parseString(xml_from_indico.read())
        agenda_items = xml_dom.getElementsByTagName("agenda_item")
        if agenda_items == 0:
            continue
        category_xml = [ '<Indico_Meetings><category_id>%s</category_id><category_name>%s</category_name>' % (category, category_names[category] ) , ]
        for item in agenda_items:
            category_xml.extend( [ "<meeting>", ] )
            try:
                start_time = item.getElementsByTagName("start_time")[0].firstChild.toxml()
            except:
                start_time = ""
            category_xml.extend( ["<start_time>%s</start_time>" % start_time, ] )
            try:
                start_date = item.getElementsByTagName("start_date")[0].firstChild.toxml()
            except:
                start_date = ""
            category_xml.extend(["<start_date>%s</start_date>" % start_date, ])
            try:
                end_date = item.getElementsByTagName("end_date")[0].firstChild.toxml()
            except:
                end_date = ""
            category_xml.extend(["<end_date>%s</end_date>" % end_date, ])
            try:
                category = item.getElementsByTagName("category")[0].firstChild.toxml()
            except:
                category = ""
            category_xml.extend(["<category>%s</category>" % category, ])
            try:
                title = item.getElementsByTagName("title")[0].firstChild.toxml()
            except:
                title = ""
            category_xml.extend(["<title>%s</title>" % title, ])
            try:
                url = item.getElementsByTagName("agenda_url")[0].firstChild.toxml()
            except:
                url = "#"
            category_xml.extend(["<url>%s</url>" % url, ])
            try:
                speaker = item.getElementsByTagName("speaker")[0].firstChild.toxml()
            except:
                speaker = ""
            category_xml.extend(["<speaker>%s</speaker>" % speaker, ])
            try:
                room = item.getElementsByTagName("room")[0].firstChild.toxml()
            except:
                room = ""
            category_xml.extend(["<room>%s</room>" % room, ])
            category_xml.extend(["</meeting>", ])
        category_xml.extend(["</Indico_Meetings>", ])
        meeting_xml_entries.append( ''.join(i.encode('utf-8')for i in category_xml) )
    meeting_xml_entries = ''.join( meeting_xml_entries )
    meeting_xml_entries = "<root>" + meeting_xml_entries + "</root>"
    """
    Add in code here to write out the XML file for submission
    """
    xml_file = """
<record>
  %(control_field)s
  <datafield tag="037" ind1=" " ind2=" ">
    <subfield code="a">XML-%(journal_name)s-%(issue_esc)s</subfield>
  </datafield>
  <datafield tag="245" ind1=" " ind2=" ">
    <subfield code="a">XML Entry for %(journal_name)s Issue %(issue)s</subfield>
  </datafield>
  <datafield tag="773" ind1=" " ind2=" ">
    <subfield code="n">%(issue)s</subfield>
    <subfield code="t">%(journal_name)s</subfield>
  </datafield>
  <datafield tag="520" ind1=" " ind2=" ">
    <subfield code="a"><![CDATA[%(xml_data)s]]></subfield>
  </datafield>
  <datafield tag="653" ind1="1" ind2=" ">
  </datafield>
  <datafield tag="980" ind1=" " ind2=" ">
    <subfield code="a">%(doc_type)s</subfield>
  </datafield>
</record>
""" % {'control_field':control_field, 'journal_name':journal_name, 'issue':issue, 'issue_esc':issue.replace('/','_'), 'xml_data': meeting_xml_entries, 'doc_type':xml_doc_type }
    """
    We have all of the XML for the meetings of the month now
    It is time to create a record for it
    """
    filename = "%s/xml_meetings_%s.xml" % (CFG_TMPDIR, journal_name + '_' + issue.replace('/','_'))
    if recid != 0:
        filename = "%s/xml_meetings_%s.xml" % (CFG_TMPDIR, recid) 
    fptr = open( filename, "w")
    fptr.write( xml_file )
    fptr.close()
    if recid == 0:
        task_low_level_submission('bibupload', 'webjournal.XML_meetings', '-i', filename)
    else:
        task_low_level_submission('bibupload', 'webjournal.XML_meetings', '-r', filename)
    return "Filename: %s <br/>Indico URL: %s <br/> Indico Categories: %s <br/> Num to display: %s <br/> XML: %s" % ( filename, indico_url, indico_categories, display_num_meetings, meeting_xml_entries )

def perform_request_issue_control(journal_name, issues,
                                  action, ln=CFG_SITE_LANG):
    """
    Central logic for issue control.

    Regenerates the flat files 'current_issue' and 'issue_group' of
    the journal that control which issue is currently active for the
    journal.

    Parameters:
        journal_name  -  the journal affected by 'action'
              issues  -  list of issues affected by 'action' TODO: check
              action  -  One of ['cfg', _('Add'), _('Refresh'),
                         _('Publish'), _('Update')]
                  ln  -  language
    """
    _ = gettext_set_language(ln)

    out = ''
    if action == "cfg" or action == _("Refresh") or action == _("Add"):
        # find out if we are in update or release
        current_issue = get_current_issue(ln, journal_name)
        grouped_issues = get_grouped_issues(journal_name, current_issue)
        if current_issue != grouped_issues[-1]:
            # The current issue has "pending updates", i.e. is grouped
            # with unreleased issues. Propose to update these issues
            next_issue = grouped_issues[grouped_issues.index(current_issue) + 1]
            out = wjt.tmpl_admin_update_issue(ln,
                                              journal_name,
                                              next_issue,
                                              current_issue)
        else:
            # Propose a release
            next_issues = get_next_journal_issues(current_issue,
                                                  journal_name,
                                                  n=get_journal_issue_grouping(journal_name))
            if action == _("Refresh"):
                next_issues += issues
                next_issues = list(set(next_issues))# avoid double entries
            elif action == _("Add"):
                next_issues += issues
                next_issues = list(set(next_issues))# avoid double entries
                next_issues.sort(compare_issues)
                highest_issue_so_far = next_issues[-1]
                one_more_issue = get_next_journal_issues(highest_issue_so_far,
                                                         journal_name,
                                                         1)
                next_issues += one_more_issue
                next_issues = list(set(next_issues)) # avoid double entries
            else:
                # get the next issue numbers to publish
                next_issues = get_next_journal_issues(current_issue,
                                                      journal_name,
                                                      n=get_journal_issue_grouping(journal_name))
            next_issues.sort(compare_issues)
            out = wjt.tmpl_admin_control_issue(ln,
                                               journal_name,
                                               next_issues)
    elif action == _("Publish"):
        # Publish the given issues (mark them as current issues)
        publish_issues = issues
        publish_issues = list(set(publish_issues)) # avoid double entries
        publish_issues.sort(compare_issues)
        if len(publish_issues) == 0:
            # User did not select an issue
            current_issue = get_current_issue(ln, journal_name)
            next_issues = get_next_journal_issues(current_issue,
                                                  journal_name,
                                                  n=get_journal_issue_grouping(journal_name))
            out = '<p style="color:#f00;text-align:center">' + \
                  _('Please select an issue') + '</p>'
            out += wjt.tmpl_admin_control_issue(ln,
                                                journal_name,
                                                next_issues)
            return out
        try:
            release_journal_issue(publish_issues, journal_name, ln)
        except InvenioWebJournalJournalIdNotFoundDBError, e:
            register_exception(req=None)
            return e.user_box()
        out = wjt.tmpl_admin_control_issue_success_msg(ln,
                                                       publish_issues,
                                                       journal_name)
        make_journal_pdfs( journal_name, publish_issues )

    elif action == _("Update"):
        try:
            try:
                update_issue = issues[0]
            except:
                raise InvenioWebJournalReleaseUpdateError(ln, journal_name)
        except InvenioWebJournalReleaseUpdateError, e:
            register_exception(req=None)
            return e.user_box()
        try:
            release_journal_update(update_issue, journal_name, ln)
        except InvenioWebJournalJournalIdNotFoundDBError, e:
            register_exception(req=None)
            return e.user_box()
        out = wjt.tmpl_admin_updated_issue_msg(ln,
                                               update_issue,
                                               journal_name)

    return out

def perform_request_alert(journal_name, issue,
                          sent, plain_text, subject, recipients,
                          html_mail, force, ln=CFG_SITE_LANG):
    """
    All the logic for alert emails.

    Display a form to edit email/recipients and options to send the
    email.  Sent in HTML/PlainText or only PlainText if wished so.
    Also prevent mistake of sending the alert more than one for a
    particular issue.

    Parameters:
        journal_name  -  the journal for which the alert is sent
               issue  -  the issue for which the alert is sent
                sent  -  Display interface to edit email if "False"
                         (string). Else send the email.
          plain_text  -  the text of the mail
             subject  -  the subject of the mail
          recipients  -  the recipients of the mail (string with
                         comma-separated emails)
           html_mail  -  if 'html', also send email as HTML (copying
                         from the current issue on the web)
               force  -  if different than "False", the email is sent
                         even if it has already been sent.
                  ln  -  language
    """
    # FIXME: more flexible options to choose the language of the alert
    languages = get_journal_languages(journal_name)
    if languages:
        alert_ln = languages[0]
    else:
        alert_ln = CFG_SITE_LANG

    if not get_release_datetime(issue, journal_name, ln):
        # Trying to send an alert for an unreleased issue
        return wjt.tmpl_admin_alert_unreleased_issue(ln,
                                                     journal_name)
    if sent == "False":
        # Retrieve default message, subject and recipients, and
        # display email editor
        subject = wjt.tmpl_admin_alert_subject(journal_name,
                                               alert_ln,
                                               issue)
        plain_text = wjt.tmpl_admin_alert_plain_text(journal_name,
                                                     alert_ln,
                                                     issue)
        plain_text = plain_text.encode('utf-8')
        recipients = get_journal_alert_recipient_email(journal_name)
        return wjt.tmpl_admin_alert_interface(ln,
                                              journal_name,
                                              subject,
                                              plain_text,
                                              recipients,
                                              alert_ln)
    else:
        # User asked to send the mail
        if was_alert_sent_for_issue(issue,
                                    journal_name,
                                    ln) != False and force == "False":
            # Mmh, email already sent before for this issue. Ask
            # confirmation
            return wjt.tmpl_admin_alert_was_already_sent(ln,
                                                         journal_name,
                                                         subject,
                                                         plain_text,
                                                         recipients,
                                                         html_mail,
                                                         issue)
        html_string = None
        if html_mail == "html":
            # Also send as HTML: retrieve from current issue
            html_file = urlopen('%s/journal/%s?ln=%s'
                                % (CFG_SITE_URL, journal_name, alert_ln))
            html_string = html_file.read()
            html_file.close()
            html_string = put_css_in_file(html_string, journal_name)
            html_string = insert_journal_link(html_string, journal_name, issue, ln)

        sender_email = get_journal_alert_sender_email(journal_name)
        send_email(sender_email, recipients, subject, plain_text,
                   html_string, header='', footer='', html_header='',
                   html_footer='', charset='utf-8')

        update_DB_for_alert(issue, journal_name, ln)
        return wjt.tmpl_admin_alert_success_msg(ln,
                                                journal_name)

def perform_request_configure(journal_name, xml_config, action, ln=CFG_SITE_LANG):
    """
    Add a new journal or configure the settings of an existing journal.

    Parameters:
        journal_name  -  the journal to configure, or name of the new journal
          xml_config  -  the xml configuration of the journal (string)
              action  -  One of ['edit', 'editDone', 'add', 'addDone']
                  ln  -  language
    """

    msg = None
    if action == 'edit':
        # Read existing config
        if journal_name is not None:
            if not can_read_xml_config(journal_name):
                return '<span style="color:#f00">Configuration could not be read. Please check that %s/webjournal/%s/%s-config.xml exists and can be read by the server.</span><br/>' % (CFG_ETCDIR, journal_name, journal_name)
            config_path = '%s/webjournal/%s/%s-config.xml' % (CFG_ETCDIR, journal_name, journal_name)
            xml_config = file(config_path).read()
        else:
            # cannot edit unknown journal...
            return '<span style="color:#f00">You must specify a journal name</span>'
    if action in ['editDone', 'addDone']:
        # Save config
        if action == 'addDone':
            res = add_journal(journal_name, xml_config)
            if res == -1:
                msg = '<span style="color:#f00">A journal with that name already exists. Please choose another name.</span>'
                action = 'add'
            elif res == -2:
                msg = '<span style="color:#f00">Configuration could not be written (no permission). Please manually copy your config to %s/webjournal/%s/%s-config.xml</span><br/>' % (CFG_ETCDIR, journal_name, journal_name)
                action = 'edit'
            elif res == -4:
                msg = '<span style="color:#f00">Cache file could not be written (no permission). Please manually create directory %s/webjournal/%s/ and make it writable for your Apache user</span><br/>' % (CFG_CACHEDIR, journal_name)
                action = 'edit'
            elif res > 0:
                msg = '<span style="color:#0f0">Journal successfully added.</span>'
                action = 'edit'
            else:
                msg = '<span style="color:#f00">An error occurred. The journal could not be added</span>'
                action = 'edit'
    if action == 'add':
        # Display a sample config.
        xml_config = '''<?xml version="1.0" encoding="UTF-8"?>
<webjournal name="AtlantisTimes">
    <view>
        <niceName>Atlantis Times</niceName>
        <niceURL>%(CFG_SITE_URL)s</niceURL>
        <css>
            <screen>/img/AtlantisTimes.css</screen>
            <print>/img/AtlantisTimes.css</print>
        </css>
        <format_template>
            <index>AtlantisTimes_Index.bft</index>
            <detailed>AtlantisTimes_Detailed.bft</detailed>
            <search>AtlantisTimes_Search.bft</search>
            <popup>AtlantisTimes_Popup.bft</popup>
            <contact>AtlantisTimes_Contact.bft</contact>
        </format_template>
    </view>

    <model>
        <record>
            <rule>News, 980__a:ATLANTISTIMESNEWS or 980__a:ATLANTISTIMESNEWSDRAFT</rule>
            <rule>Science, 980__a:ATLANTISTIMESSCIENCE or 980__a:ATLANTISTIMESSCIENCEDRAFT</rule>
            <rule>Arts, 980__a:ATLANTISTIMESARTS or 980__a:ATLANTISTIMESARTSDRAFT</rule>
        </record>
    </model>

    <controller>
        <issue_grouping>2</issue_grouping>
	<issues_per_year>52</issues_per_year>
	<hide_unreleased_issues>all</hide_unreleased_issues>
        <marc_tags>
            <issue_number>773__n</issue_number>
	    <order_number>773__c</order_number>
        </marc_tags>
	<alert_sender>%(CFG_SITE_SUPPORT_EMAIL)s</alert_sender>
	<alert_recipients>recipients@atlantis.atl</alert_recipients>
	<languages>en,fr</languages>
	<submission>
            <doctype>DEMOJRN</doctype>
            <report_number_field>DEMOJRN_RN</report_number_field>
	</submission>
        <first_issue>02/2009</first_issue>
        <draft_keyword>DRAFT</draft_keyword>
    </controller>
</webjournal>''' % {'CFG_SITE_URL': CFG_SITE_URL,
                    'CFG_SITE_SUPPORT_EMAIL': CFG_SITE_SUPPORT_EMAIL}

    out = wjt.tmpl_admin_configure_journal(ln=ln,
                                           journal_name=journal_name,
                                           xml_config=xml_config,
                                           action=action,
                                           msg=msg)

    return out

######################## ADDING/REMOVING JOURNALS ###############################

def add_journal(journal_name, xml_config):
    """
    Add a new journal to the DB. Also create the configuration file

    Parameters:
         journal_name  -  the name (used in URLs) of the new journal
           xml_config  -  the xml configuration of the journal (string)
    Returns:
         the id of the journal if successfully added
         -1 if could not be added because journal name already exists
         -2 if config could not be saved
         -3 if could not be added for other reasons
         -4 if database cache could not be added
    """
    try:
        get_journal_id(journal_name)
    except InvenioWebJournalJournalIdNotFoundDBError:
        # Perfect, journal does not exist
        res = run_sql("INSERT INTO jrnJOURNAL (name) VALUES(%s)", (journal_name,))
        # Also save xml_config
        config_dir = '%s/webjournal/%s/' % (CFG_ETCDIR, journal_name)
        try:
            if not os.path.exists(config_dir):
                os.makedirs(config_dir)
            xml_config_file = file(config_dir + journal_name + '-config.xml', 'w')
            xml_config_file.write(xml_config)
            xml_config_file.close()
        except Exception:
            res = -2
        # And save some info in file in case database is down
        journal_info_path = get_journal_info_path(journal_name)
        journal_info_dir = os.path.dirname(journal_info_path)
        if not os.path.exists(journal_info_dir):
            try:
                os.makedirs(journal_info_dir)
            except Exception:
                if res <= 0:
                    res = -4
        journal_info_file = open(journal_info_path, 'w')

        cPickle.dump({'journal_id': res,
                      'journal_name': journal_name,
                      'current_issue':'01/2000'}, journal_info_file)
        return res
    return -1

def remove_journal(journal_name):
    """
    Remove a journal from the DB.  Does not completely remove
    everything, in case it was an error from the editor..

    Parameters:
         journal_name  -  the journal to remove

    Returns:
         the id of the journal if successfully removed or
         -1 if could not be removed because journal name does not exist or
         -2 if could not be removed for other reasons
    """
    run_sql("DELETE FROM jrnJOURNAL WHERE name=%s", (journal_name,))

######################## TIME / ISSUE FUNCTIONS ###############################


def release_journal_issue(publish_issues, journal_name, ln=CFG_SITE_LANG):
    """
    Releases a new issue.

    This sets the current issue in the database to 'publish_issues' for
    given 'journal_name'

    Parameters:
         journal_name  -  the journal for which we release a new issue
       publish_issues  -  the list of issues that will be considered as
                          current (there can be several)
                   ln  -  language
    """
    journal_id = get_journal_id(journal_name, ln)
    if len(publish_issues) > 1:
        publish_issues.sort(compare_issues)
        low_bound = publish_issues[0]
        high_bound = publish_issues[-1]
        issue_display = '%s-%s/%s' % (low_bound.split("/")[0],
                                      high_bound.split("/")[0],
                                      high_bound.split("/")[1])
        # remember convention: if we are going over a new year, take the higher
    else:
        issue_display = publish_issues[0]
    # produce the DB lines
    for publish_issue in publish_issues:
        move_drafts_articles_to_ready(journal_name, publish_issue)
        run_sql("INSERT INTO jrnISSUE (id_jrnJOURNAL, issue_number, issue_display) \
                VALUES(%s, %s, %s)", (journal_id,
                                      publish_issue,
                                      issue_display))
    # set first issue to published
    release_journal_update(publish_issues[0], journal_name, ln)

    # update information in file (in case DB is down)
    journal_info_path = get_journal_info_path(journal_name)
    journal_info_file = open(journal_info_path, 'w')
    cPickle.dump({'journal_id': journal_id,
                  'journal_name': journal_name,
                  'current_issue': get_current_issue(ln, journal_name)},
                 journal_info_file)

def delete_journal_issue(issue, journal_name, ln=CFG_SITE_LANG):
    """
    Deletes an issue from the DB.
    (Not currently used)
    """
    journal_id = get_journal_id(journal_name, ln)
    run_sql("DELETE FROM jrnISSUE WHERE issue_number=%s \
            AND id_jrnJOURNAL=%s",(issue, journal_id))

    # update information in file (in case DB is down)
    journal_info_path = get_journal_info_path(journal_name)
    journal_info_file = open(journal_info_path, 'w')
    cPickle.dump({'journal_id': journal_id,
                  'journal_name': journal_name,
                  'current_issue': get_current_issue(ln, journal_name)},
                 journal_info_file)

def was_alert_sent_for_issue(issue, journal_name, ln):
    """
    Returns False if alert has not already been sent for given journal and
    issue, else returns time of last alert, as time tuple

    Parameters:
         journal_name  -  the journal for which we want to check last alert
                issue  -  the issue for which we want to check last alert
                   ln  -  language
    Returns:
         time tuple or False. Eg: (2008, 4, 25, 7, 58, 37, 4, 116, -1)
    """
    journal_id = get_journal_id(journal_name, ln)
    date_announced = run_sql("SELECT date_announced FROM jrnISSUE \
                                WHERE issue_number=%s \
                                AND id_jrnJOURNAL=%s", (issue, journal_id))[0][0]
    if date_announced == None:
        return False
    else:
        return date_announced.timetuple()

def update_DB_for_alert(issue, journal_name, ln):
    """
    Update the 'last sent alert' timestamp for the given journal and
    issue.

    Parameters:
         journal_name  -  the journal for which we want to update the time
                          of last alert
                issue  -  the issue for which we want to update the time
                          of last alert
                   ln  -  language
    """
    journal_id = get_journal_id(journal_name, ln)
    run_sql("UPDATE jrnISSUE set date_announced=NOW() \
                WHERE issue_number=%s \
                AND id_jrnJOURNAL=%s", (issue,
                                        journal_id))

def release_journal_update(update_issue, journal_name, ln=CFG_SITE_LANG):
    """
    Releases an update to a journal.
    """
    move_drafts_articles_to_ready(journal_name, update_issue)
    journal_id = get_journal_id(journal_name, ln)
    run_sql("UPDATE jrnISSUE set date_released=NOW() \
                WHERE issue_number=%s \
                AND id_jrnJOURNAL=%s", (update_issue,
                                        journal_id))

def move_drafts_articles_to_ready(journal_name, issue):
    """
    Move draft articles to their final "collection".

    To do so we rely on the convention that an admin-chosen keyword
    must be removed from the metadata
    """
    protected_datafields = ['100', '245', '246', '520', '590', '700']
    keyword_to_remove = get_journal_draft_keyword_to_remove(journal_name)

    categories = get_journal_categories(journal_name, issue)
    for category in categories:
        articles = get_journal_articles(journal_name, issue, category)
        for order, recids in articles.iteritems():
            for recid in recids:
                record_xml = format_record(recid, of='xm')
                if not record_xml:
                    continue
                new_record_xml_path = os.path.join(CFG_TMPDIR,
                                                   'webjournal_publish_' + \
                                                   str(recid) + '.xml')
                if os.path.exists(new_record_xml_path):
                    # Do not modify twice
                    continue
                record_struc = create_record(record_xml)
                record = record_struc[0]
                new_record = update_draft_record_metadata(record,
                                                          protected_datafields,
                                                          keyword_to_remove)
                new_record_xml = print_rec(new_record)
                if new_record_xml.find(keyword_to_remove) >= 0:
                    new_record_xml = new_record_xml.replace(keyword_to_remove, '')
                    # Write to file
                    new_record_xml_file = file(new_record_xml_path, 'w')
                    new_record_xml_file.write(new_record_xml)
                    new_record_xml_file.close()
                    # Submit
                    task_low_level_submission('bibupload',
                                              'WebJournal',
                                              '-c', new_record_xml_path)

def update_draft_record_metadata(record, protected_datafields, keyword_to_remove):
    """
    Returns a new record with fields that should be modified in order
    for this draft record to be considered as 'ready': keep only
    controlfield 001 and non-protected fields that contains the
    'keyword_to_remove'

    Parameters:
                  record - a single recored (as BibRecord structure)

    protected_datafields - *list* tags that should not be part of the
                           returned record

       keyword_to_remove - *str* keyword that should be considered
                           when checking if a field should be part of
                           the returned record.
    """
    new_record = {}
    for tag, field in record.iteritems():
        if tag in protected_datafields:
            continue
        elif not keyword_to_remove in str(field) and \
                 not tag == '001':
            continue
        else:
            # Keep
            new_record[tag] = field

    return new_record

######################## XML CONFIG ###############################

def can_read_xml_config(journal_name):
    """
    Check that configuration xml for given journal name is exists and
    can be read.
    """
    config_path = '%s/webjournal/%s/%s-config.xml' % \
                  (CFG_ETCDIR, journal_name, journal_name)
    try:
        file(config_path).read()
    except IOError:
        return False

    return True

######################## EMAIL HELPER FUNCTIONS ###############################

def insert_journal_link(html_string, journal_name, issue, ln):
    """
    Insert a warning regarding HTML formatting inside mail client and
    link to journal page just after the body of the page.

    @param html_string: the HTML newsletter
    @param journal_name: the journal name
    @param issue: journal issue for which the alert is sent (in the form number/year)
    @param ln: language
    """
    def replace_body(match_obj):
        "Replace body with itself + header message"
        header = wjt.tmpl_admin_alert_header_html(journal_name, ln, issue)
        return match_obj.group() + header
    return re.sub('<body.*?>', replace_body, html_string, 1)

def put_css_in_file(html_message, journal_name):
    """
    Retrieve the CSS of the journal and insert/inline it in the <head>
    section of the given html_message. (Used for HTML alert emails)

    Parameters:
          journal_name  -  the journal name
          html_message  -  the html message (string) in which the CSS
                           should be inserted
    Returns:
          the HTML message with its CSS inlined
    """
    css_path = get_journal_css_url(journal_name)
    if not css_path:
        return
    css_file = urlopen(css_path)
    css = css_file.read()
    css = make_full_paths_in_css(css, journal_name)
    html_parted = html_message.split("</head>")
    if len(html_parted) > 1:
        html = '%s<style type="text/css">%s</style></head>%s' % (html_parted[0],
                                                        css,
                                                        html_parted[1])
    else:
        html_parted = html_message.split("<html>")
        if len(html_parted) > 1:
            html = '%s<html><head><style type="text/css">%s</style></head>%s' % (html_parted[0],
                                                                                 css,
                                                                                 html_parted[1])
        else:
            return
    return html

def make_full_paths_in_css(css, journal_name):
    """
    Update the URLs in a CSS from relative to absolute URLs, so that the
    URLs are accessible from anywhere (Used for HTML alert emails)

    Parameters:
          journal_name  -  the journal name
                   css  -  a cascading stylesheet (string)
    Returns:
          (str) the given css with relative paths converted to absolute paths
    """
    url_pattern = re.compile('''url\(["']?\s*(?P<url>\S*)\s*["']?\)''',
                             re.DOTALL)
    url_iter = url_pattern.finditer(css)
    rel_to_full_path = {}
    for url in url_iter:
        url_string = url.group("url")
        url_string = url_string.replace('"', "")
        url_string = url_string.replace("'", "")
        if url_string[:6] != "http://":
            rel_to_full_path[url_string] = '"%s/img/webjournal_%s/%s"' % \
            (CFG_SITE_URL,
            journal_name,
            url_string)
    for url in rel_to_full_path.keys():
        css = css.replace(url, rel_to_full_path[url])
    return css
