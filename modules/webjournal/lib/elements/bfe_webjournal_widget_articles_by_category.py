# -*- coding: utf-8 -*-
## $Id: bfe_webjournal_widget_whatsNew.py,v 1.24 2009/01/27 07:25:12 jerome Exp $
##
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
WebJournal widget - Display the index of the lastest articles for this issue, 
optionally sorted by category. See below for more details. 
"""
import time
import os

from invenio.dbquery import run_sql
from invenio.search_engine import search_pattern
from invenio.bibformat_engine import BibFormatObject
from invenio.config import \
     CFG_SITE_URL, \
     CFG_CACHEDIR, \
     CFG_ACCESS_CONTROL_LEVEL_SITE, \
     CFG_CERN_SITE
from invenio.webjournal_utils import \
     parse_url_string, \
     make_journal_url, \
     get_journal_info_path, \
     get_journal_categories, \
     get_journal_articles, \
     get_current_issue
from invenio.messages import gettext_set_language

import xml.etree.ElementTree as ET


def format(bfo, latest_issue_only='yes', newest_articles_only='yes',
           link_category_headers='yes', display_categories='', hide_when_only_new_records="no", 
           subject_to_css_class_kb="WebJournalSubject2CSSClass", sort_by_topic_field="", category_to_display='', display_titles="no",
           display_headers="yes", display_category_header="no"
           ):
    """
    Display the index to the newest articles (of the latest issue, or of the displayed issue)

    @param latest_issue_only: if 'yes', always display articles of the latest issue, even if viewing a past issue
    @param newest_articles_only: only display new articles, not those that also appeared in previous issues
    @param link_category_headers: if yes, category headers link to index page of that category
    @param display_categories: comma-separated list of categories to display. If none, display all
    @param hide_when_only_new_records: if 'yes' display new articles only if old articles exist in this issue
    @param subject_to_css_class_kb: knowledge base that maps 595__a to a CSS class
    @sort_by_topic: whether or not to group the articles by their 60517 field
    @category_to_display: the string name of the category to display (the category as defined in the webjournal configuration xml file)
    @display_titles: Whether or not to display the actual article titles, or instead use the subcategory 
    @display_headers: whether or not to display the subcategory headers 
    @display_category_header: whether to print the category name at the top above the list of articles
    """
    args = parse_url_string(bfo.user_info['uri'])
    journal_name = args["journal_name"]
    ln = args["ln"]
    _ = gettext_set_language(ln)

    if latest_issue_only.lower() == 'yes':
        issue_number = get_current_issue(bfo.lang, journal_name)
    else:
        issue_number = args["issue"]

    # Try to get HTML from cache
    if args['verbose'] == 0:
        cached_html = _get_whatsNew_from_cache(journal_name, issue_number, ln, category_to_display)
        if cached_html:
            return cached_html

    # No cache? Build from scratch
    # 1. Get the articles
    journal_categories = get_journal_categories(journal_name,
                                                issue_number)
    if display_categories:
        display_categories = display_categories.lower().split(',')
        journal_categories = [category for category in journal_categories \
                              if category.lower() in display_categories]
    whats_new_articles = {}
    for category in journal_categories:
        whats_new_articles[category] = get_journal_articles(journal_name,
                                                            issue_number,
                                                            category,
                                                            newest_only=newest_articles_only.lower() == 'yes')

    # Do we want to display new articles only if they have been added
    # to an issue that contains non-new records?
    if hide_when_only_new_records.lower() == "yes":
        # First gather all articles in this issue
        all_whats_new_articles = {}
        for category in journal_categories:
            all_whats_new_articles[category] = get_journal_articles(journal_name,
                                                                    issue_number,
                                                                    category,
                                                                    newest_first=True,
                                                                    newest_only=False)
        # Then check if we have some articles at position > -1
        has_old_articles = False
        for articles in all_whats_new_articles.values():
            if len([order for order in articles.keys() if order > -1]) > 0:
                has_old_articles = True
                break
        if not has_old_articles:
            # We don't have old articles? Thend don't consider any
            for category in journal_categories:
                whats_new_articles[category] = {}

    # 2. Build the HTML
    html_out = u''

    topics_empty = find_topics( sort_by_topic_field ) 

    for category in journal_categories:
        if category_to_display != "":
            if category_to_display != category:
                continue
        topics = ET.fromstring(  topics_empty )
        articles_in_category = whats_new_articles[category]
        html_articles_in_category = u""
        # Generate the list of articles in this category
        order_numbers = articles_in_category.keys()
        for order in order_numbers:
            articles = articles_in_category[order]
            for recid in articles:
                article_topic = ""
                link = make_journal_url(bfo.user_info['uri'], {'journal_name': journal_name,
                                                               'issue_number': issue_number.split('/')[0],
                                                               'issue_year': issue_number.split('/')[1],
                                                               'category': category,
                                                               'recid': recid,
                                                               'ln': bfo.lang})
                temp_rec = BibFormatObject(recid)
                notes = temp_rec.fields('595__a')
                css_classes = [temp_rec.kb(subject_to_css_class_kb, note, None) \
                           for note in notes]
                css_classes = [css_class for css_class in css_classes \
                           if css_class is not None]
                
                if ln == 'fr':
                    try:
                        title = temp_rec.fields('246_1a')[0]
                    except:
                        continue
                else:
                    try:
                        title = temp_rec.field('245__a')
                    except:
                        continue

                article_topic = temp_rec.field('65017a')
                try:
                    subcats = topics.findall( "category/subcategory" )
                    for cat in subcats:
                        if cat.get( "name" ).lower() == article_topic.lower():
                            article = ET.SubElement( cat, "article" )
                            article.set( "title", title.decode('utf-8') )
                            article.set( "classes", ' '.join(css_classes) )
                            article.set( "link", link )
                except:
                    pass

                try:
                    html_articles_in_category += u'<li class="%s"><a href="%s">%s</a></li>' % \
                                                 ( ' '.join(css_classes), link, title.decode('utf-8'))
                except:
                    pass

        #Print out all of the stories now
        if html_articles_in_category:
            if display_category_header == "yes":
                html_out += '<a href="'
                html_out += make_journal_url(bfo.user_info['uri'],
                                             {'journal_name': journal_name,
                                              'issue_number': issue_number.split('/')[0],
                                              'issue_year': issue_number.split('/')[1],
                                              'category': category,
                                              'recid': '',
                                              'ln': bfo.lang})
                html_out += '" class="whatsNewCategory"> <b><u> %s </u></b></a> <br/>' % category

            categories = topics.findall( "category" )
            for category_topic in categories:
                content = ""
                subcategories = category_topic.findall( "subcategory" )
                for subcategory in subcategories:
                    if len( subcategory.getchildren() ) > 0:
                        content_articles = ""
                        for article in subcategory.getchildren():
                            if display_titles == "no":
                                content += '<dd class="%s" ><a href="%s" > %s  </a> </dd>' % ( article.get("classes"), article.get("link"), subcategory.get("title") )
                            else:
                                content += '<li class="%s" ><a href="%s" > %s  </a> </li>' % ( article.get("classes"), article.get("link"), article.get("title") )
                if content != "":
                    if display_headers == "yes":
                        html_out += " <dl><dt> %s </dt> %s </dl>" % ( category_topic.get("title"), content )
                    else:
                        html_out += "<ul> %s </ul>" % ( content )

    if not html_out:
        html_out = '<i>' + _('There are no new articles for the moment') + '</i>'

    if args['verbose'] == 0:
        cache_whatsNew(html_out.encode('utf-8'), journal_name, issue_number, ln)
    return html_out.encode('utf-8')

def _get_whatsNew_from_cache(journal_name, issue, ln, category):
    """
    Try to get the navigation section box from cache.
    """
    cache_path = os.path.realpath('%s/webjournal/%s/%s_whatsNew_%s_%s.html' % \
                                  (CFG_CACHEDIR,
                                   journal_name,
                                   issue.replace('/','_'),
                                   ln, category))
    if not cache_path.startswith(CFG_CACHEDIR + '/webjournal'):
        # Make sure we are reading from correct directory (you
        # know, in case there are '../../' inside journal name..)
        return False
    try:
        last_update = os.path.getctime(cache_path)
    except:
        return False

    try:
        # Get last journal update, based on journal info file last
        # modification time
        journal_info_path = get_journal_info_path(journal_name)
        last_journal_update = os.path.getctime(journal_info_path)
    except:
        return False

    now = time.time()
    if ((last_update + 30*60) < now) or \
           (last_journal_update > last_update):
        # invalidate after 30 minutes or if last journal release is
        # newer than cache
        return False
    try:
        cached_file = open(cache_path).read()
    except:
        return False

    return cached_file

def cache_whatsNew(html, journal_name, issue, ln):
    """
    caches the whats new box for 30 minutes.
    """
    if not CFG_ACCESS_CONTROL_LEVEL_SITE == 2:
        cache_path = os.path.realpath('%s/webjournal/%s/%s_whatsNew_%s.html' % \
                                      (CFG_CACHEDIR,
                                       journal_name,
                                       issue.replace('/','_'),
                                       ln))
        if cache_path.startswith(CFG_CACHEDIR + '/webjournal'):
            # Do not try to cache if the journal name led us to some
            # other directory ('../../' inside journal name for
            # example)
            cache_dir = CFG_CACHEDIR + '/webjournal/' + journal_name
            if not os.path.isdir(cache_dir):
                os.makedirs(cache_dir)
            cache_file = file(cache_path, "w")
            cache_file.write(html)
            cache_file.close()

def escape_values(bfo):
    """
    Called by BibFormat in order to check if output of this element
    should be escaped.
    """
    return 0

def find_topics( fieldname="" ):
    """
    This function queries the database to determine the categories 
    associated with a particular submission type
    as defined in WebSubmit
    """
    res = run_sql("SELECT fidesc FROM sbmFIELDDESC WHERE  name=%s", (fieldname,))
    the_xml = ET.fromstring( res[0][0] )
    groups = the_xml.findall( "optgroup" )
    new_xml = ET.Element( "root" )

    for item in groups:
        main_group = ET.SubElement( new_xml, "category" )
        main_group.set( "title", item.get("label") )
        for opt in item.findall("option"):
            if new_xml.find( opt.get("value") ) == None:
                sub_group = ET.SubElement( main_group, "subcategory" )
                sub_group.set( "name", opt.get("value") ) 
                sub_group.set( "title", opt.text )
    return ET.tostring( new_xml )

