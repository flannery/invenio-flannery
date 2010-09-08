# -*- coding: utf-8 -*-
## $Id: bfe_webjournal_MainArticleOverview.py,v 1.28 2009/02/12 10:00:57 jerome Exp $
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
WebJournal Element - Creates an overview of all the articles of a
certain category in one specific issue.
"""
import re
import os
import urllib
import xml.etree.ElementTree as ET

import invenio.bibformat_elements.bfe_webjournal_article_body as body_formatter

try:
    from PIL import Image
    PIL_imported = True
except ImportError:
    PIL_imported = False
from invenio.bibformat_engine import BibFormatObject
from invenio.htmlutils import HTMLWasher, remove_html_markup
from invenio.messages import gettext_set_language
from invenio.config import \
     CFG_ACCESS_CONTROL_LEVEL_SITE, \
     CFG_TMPDIR, \
     CFG_CERN_SITE, \
     CFG_SITE_LANG, \
     CFG_ETCDIR
from invenio.webjournal_utils import \
     cache_index_page, \
     get_index_page_from_cache, \
     parse_url_string, \
     make_journal_url, \
     get_journal_articles, \
     issue_is_later_than, \
     get_current_issue, \
     get_journal_categories
from invenio.webjournal_utils import \
     image_pattern, \
     img_pattern, \
     header_pattern, \
     header_pattern2, \
     para_pattern
from invenio.urlutils import create_html_link
from invenio.bibdocfile import decompose_file
from invenio.dbquery import run_sql

from urlparse import urlparse


def format(bfo, number_of_featured_articles="1",
           number_of_articles_with_image="3", new_articles_first='yes',
           image_px_width="300", small_image_px_width="200",
           subject_to_css_class_kb="WebJournalSubject2CSSClass",
           link_image_to_article='yes', image_alignment='left',
           topic_class='topic_class', sort_by_topic_field=''):
    """
    Creates an overview of all the articles of a certain category in one
    specific issue.

    Note the following:
    <ul>
    <li>The element consider only the latest issue: when viewing
    archives of your journal, readers will see the newest articles of
    the latest issue, not the ones of the issue they are looking
    at</li>

    <li>This is not an index of the articles of the latest issue: it
    display only <b>new</b> articles, that is articles that have never
    appeared in a previous issue</li>

    <li>This element produces a table-based layout, in order to have a
    more or less readable HTML alert when sent some Email clients
    (Outlook 2007)</li>

    <li>When producing the HTML output of images, this element tries to
    insert the width and height attributes to the img tag: this is
    necessary in order to produce nice HTML alerts. This dimension
    therefore overrides any dimension defined in the CSS. The Python
    Image Library (PIL) should be installed for this element to
    recognize the size of images.</li>
    </ul>

    @param number_of_featured_articles: the max number of records with emphasized title
    @param number_of_articles_with_image: the max number of records for which their image is displayed
    @param new_articles_first: if 'yes', display new articles before other articles
    @param image_px_width: (integer) width of first image featured on this page
    @param small_image_px_width: (integer) width of small images featured on this page
    @param subject_to_css_class_kb: knowledge base that maps 595__a to a CSS class
    @param link_image_to_article: if 'yes', link image (if any) to article
    @param image_alignment: 'left', 'center' or 'right'. To help rendering in Outlook.
    @param topic_class: the class to apply to the span for the topic.
    """
    args = parse_url_string(bfo.user_info['uri'])
#    url_params = urlparse( bfo.user_info['uri'] )[4]
#    return args
#    return dict([part.split('=') for part in url_params.split('&') \
#                           if len(part.split('=')) == 2])
#    bfo.user_info['uri']
#    return bfo.user_info['uri']
#    return dumpObj( bfo.user_info['uri'] )
#    return "HELLLO"
#    return prettyPrint( dumpObj(args), split="<br/>" )
    journal_name = args["journal_name"]
#    return find_topics( journal_name )
    this_issue_number = args["issue"]
#    category_name = args["category"]
    verbose = args["verbose"]
    ln = args["ln"]
    _ = gettext_set_language(ln)

    if image_px_width.isdigit():
        image_px_width = int(image_px_width)
    else:
        image_px_width = None
    if small_image_px_width.isdigit():
        small_image_px_width = int(small_image_px_width)
    else:
        small_image_px_width = None

    # We want to put emphasis on the n first articles (which are not
    # new)
    if number_of_featured_articles.isdigit():
        number_of_featured_articles = int(number_of_featured_articles)
    else:
        number_of_featured_articles = 0

    # Only n first articles will display images
    if number_of_articles_with_image.isdigit():
        number_of_articles_with_image = int(number_of_articles_with_image)
    else:
        number_of_articles_with_image = 0
    # Help image alignement without CSS, to have better rendering in Outlook
    img_align = ''
    if image_alignment:
        img_align = 'align="%s"' % image_alignment

    # Try to get the page from cache. Only if issue is older or equal
    # to latest release.
    latest_released_issue = get_current_issue(ln, journal_name)
    """    if verbose == 0 and not issue_is_later_than(this_issue_number,
                                                latest_released_issue):
        cached_html = get_index_page_from_cache(journal_name, category_name,
                                                this_issue_number, ln)
        if cached_html:
            return cached_html
    """

    # Retrieve categories for this journal and issue
    journal_categories = get_journal_categories(journal_name, )
    html = ""
    for category_name in journal_categories:
        out = "<h1 class='category_title'>%s</h1><ul>" % category_name

       # Get the id list
        ordered_articles = get_journal_articles(journal_name,
                                                this_issue_number,
                                                category_name,
                                                newest_first=new_articles_first.lower() == 'yes')
        new_articles_only = False
        if ordered_articles.keys() and max(ordered_articles.keys()) < 0:
            # If there are only new articles, don't bother marking them as
            # new
            new_articles_only = True

        order_numbers = ordered_articles.keys()
        order_numbers.sort()
        img_css_class = "featuredImageScale"
        topics = ET.fromstring( find_topics( journal_name ) )
        if len(order_numbers) < 4:
            column = 0
        else:
            column = 1
        i = 0    
        for order_number in order_numbers:
            for article_id in ordered_articles[order_number]:
                # A record is considered as new if its position is
                # negative and there are some non-new articles
                article_is_new = (order_number < 0 and not new_articles_only)

                temp_rec = BibFormatObject(article_id)
                article_topic = temp_rec.field('65017a')

                main_topics = topics.findall( "category" )
                for subtopics in main_topics:
                    for topic in subtopics:
                        if topic.get('name') == article_topic:
                            topic_title = subtopics.get('title')

                title = ''
                if ln == "fr":
                    title = temp_rec.field('246_1a')
                    if title == '':
                        title = temp_rec.field('245__a')
                else:
                    title = temp_rec.field('245__a')
                    if title == '':
                        title = temp_rec.field('246_1a')
                author = temp_rec.field('100__a')

                # Get CSS class (if relevant)
                notes = temp_rec.fields('595__a')
                css_classes = [temp_rec.kb(subject_to_css_class_kb, note, None) \
                               for note in notes]
                css_classes = [css_class for css_class in css_classes \
                               if css_class is not None]

                if article_is_new:
                    css_classes.append('new')

                # Maybe we want to force image to appear?
                display_image_on_index = False
                if 'display_image_on_index' in notes:
                    display_image_on_index = True

                # Build generic link to this article
                article_link = make_journal_url(bfo.user_info['uri'], {'recid':str(article_id),
                                                                       'ln': bfo.lang})

                # Build the "more" link
                more_link = '''<a class="readMore" title="link to the article" href="%s"> read more... </a>
                            ''' % (article_link)

                text = body_formatter.format( temp_rec )
                out += '''
                        <h%(header_tag_size)s class="%(css_classes)s articleTitle" style="clear:both;">
                            <span class="%(topic_class)s">%(topic_title)s </span>%(title)s
                        </h%(header_tag_size)s>
                        <div class="articleBody">
                            %(text)s
                            -- %(author)s
                        </div>
                        <hr/>
                        </li>
                         ''' % {'title': title,
                                'text': text,
                                'author': author,
    #                            'css_classes': ' '.join(css_classes),
                                'css_classes': ' ',
                                'header_tag_size': "2",
                                'topic_class':topic_class,
                                'topic_title':topic_title}

        out += '</ul>'
        if verbose == 0 and not CFG_ACCESS_CONTROL_LEVEL_SITE == 2 :
            cache_index_page(out, journal_name, category_name,
                             this_issue_number, ln)

        html += out
    return html
def escape_values(bfo):
    """
    Called by BibFormat in order to check if output of this element
    should be escaped.
    """
    return 0

def _get_feature_image(record, ln=CFG_SITE_LANG):
    """
    Looks for an image that can be featured on the article overview page.
    """
    src = ''
    if ln == "fr":
        article = ''.join(record.fields('590__b'))
        if not article:
            article = ''.join(record.fields('520__b'))
    else:
        article = ''.join(record.fields('520__b'))
        if not article:
            article = ''.join(record.fields('590__b'))

    image = re.search(img_pattern, article)
    if image:
        src = image.group("image")
    if not src:
        # Look for an attached image
        icons = [icon for icon in record.fields('8564_q') if \
                (decompose_file(icon)[2] in ['jpg', 'jpeg', 'png', 'gif'])]
        if icons:
            src = icons[0]
    return src

def _get_first_sentence_or_part(header_text):
    """
    Tries to cut the text at the end of the first sentence or an empty space
    between char 200 and 300. Else return 250 first chars.
    """
    header_text = header_text.lstrip()
    first_sentence = header_text[100:].find(".")
    if first_sentence == -1:
        # try question mark
        first_sentence = header_text[100:].find("?")
    if first_sentence == -1:
        # try exclamation mark
        first_sentence = header_text[100:].find("!")
    if first_sentence != -1 and first_sentence < 250:
        return "%s." % header_text[:(100+first_sentence)]
    else:
        an_empty_space = header_text[200:].find(" ")
        if an_empty_space != -1 and an_empty_space < 300:
            return "%s..." % header_text[:(200+an_empty_space)]
        else:
            return "%s..." % header_text[:250]

def _get_feature_text(record, language):
    """
    Looks for a text (header) that can be featured on the article overview
    page.
    """
    washer = HTMLWasher()
    header_text = ""
    # Check if there is a header
    if language == "fr":
        header = record.field('590__a')
        if header.strip() in \
               ['', '<br/>', '<!--HTML--><br />', '<!--HTML-->']:
            header = record.field('520__a')
    else:
        header = record.field('520__a')
        if header.strip() in \
               ['', '<br/>', '<!--HTML--><br />', '<!--HTML-->']:
            header = record.field('590__a')
    header = washer.wash(html_buffer=header,
                         allowed_tag_whitelist=[],
                         allowed_attribute_whitelist=[])
    if header != "":
        header_text = header
    else:
        if language == "fr":
            article = record.fields('590__b')
            if not article or \
                   (len(article) == 1 and \
                    article[0].strip() in \
                    ['', '<br />', '<!--HTML--><br />', '<!--HTML-->']):
                article = record.fields('520__b')
        else:
            article = record.fields('520__b')
            if not article or \
                   (len(article) == 1 and \
                    article[0].strip() in \
                    ['', '<br />', '<!--HTML--><br />', '<!--HTML-->']):
                article = record.fields('590__b')
        try:
            article = article[0]
        except:
            return ''

        match_obj = re.search(header_pattern, article)
        if not match_obj:
            match_obj = re.search(header_pattern2, article)
        try:
            header_text = match_obj.group("header")
            header_text = washer.wash(html_buffer=header_text,
                                      allowed_tag_whitelist=['a'],
                                      allowed_attribute_whitelist=['href',
                                                                   'target',
                                                                   'class'])
            if header_text == "":
                raise Exception
        except:
            article = article.replace(header_text, '')
            article = article.replace('<p/>', '')
            article = article.replace('<p>&nbsp;</p>', '')
            match_obj = re.search(para_pattern, article)
            try:
                # get the first paragraph
                header_text = match_obj.group("paragraph")
                try:
                    header_text = washer.wash(html_buffer=header_text,
                                              allowed_tag_whitelist=[],
                                              allowed_attribute_whitelist=[])
                except:
                    # was not able to parse correctly the HTML. Use
                    # this safer function, but producing less good
                    # results
                    header_text = remove_html_markup(header_text)

                if header_text.strip() == "":
                    raise Exception
                else:
                    if len(header_text) > 250:
                        header_text = _get_first_sentence_or_part(header_text)
            except:
                # in a last instance get the first sentence
                try:
                    article = washer.wash(article,
                                          allowed_tag_whitelist=[],
                                          allowed_attribute_whitelist=[])
                except:
                    # was not able to parse correctly the HTML. Use
                    # this safer function, but producing less good
                    # results
                    article = remove_html_markup(article)

                header_text = _get_first_sentence_or_part(article)

    return header_text

def find_topics( journal_name="" ):
    """
    This function queries the WJ config file to determine the categories 
    associated with a particular submission type
    as defined in WebSubmit
    """
    # Grab the journal configuration file and build a list of what titles correspond to what abbreviations 
    # to be used when building the layout
    config_path = '%s/webjournal/%s/%s-config.xml' % \
                  (CFG_ETCDIR, journal_name, journal_name)
    config_xml = ET.parse( config_path )
    the_xml = ET.fromstring( config_xml.find( "controller/article_categories" ).text )
    groups = the_xml.findall( "optgroup" )
    new_xml = ET.Element( "root" )

    for item in groups:
        main_group = ET.SubElement( new_xml, "category" )
        main_group.set( "title", item.get("label") )
        main_group.set( "name", item.get("value") )
        for opt in item.findall("option"):
            if new_xml.find( opt.get("value") ) == None:
                sub_group = ET.SubElement( main_group, "subcategory" )
                sub_group.set( "name", opt.get("value") ) 
                sub_group.set( "title", opt.text )
    return ET.tostring( new_xml )


#print format( "PMreport" )
