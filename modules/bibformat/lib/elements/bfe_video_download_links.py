# -*- coding: utf-8 -*-
##
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
"""BibFormat element - Prints a links to fulltext
"""
__revision__ = "$Id$"

import re
from invenio.bibdocfile import BibRecDocs, file_strip_ext
from invenio.messages import gettext_set_language
from invenio.config import CFG_SITE_URL, CFG_CERN_SITE
from cgi import escape
from urlparse import urlparse
from os.path import basename
import urllib

from hachoir_core.error import HachoirError
from hachoir_core.cmd_line import unicodeFilename
from hachoir_parser import createParser
from hachoir_core.tools import makePrintable
from hachoir_metadata import extractMetadata

def format(bfo, download_movie_table_class='download_movie_table'):
    """
     ENTER DESCRIPTION
    """
    _ = gettext_set_language(bfo.lang)

    wm = ""
    wm_links = ""
    flv = ""
    flv_links = ""
    other = ""
    other_links = ""

    files = get_files(bfo)
    for fileinfo in files:
        (name, path, url, width, height, streamtype, extension, mime) = fileinfo
        if streamtype == "video":
            if extension == "flv":
                flv = flv + "<a href='%(url)s' target='_blank'>%(width)sx%(height)s</a> %(filetype)s (%(mime)s)<br/>" % { 'url':url, 'width':width, 'height':height,'filetype':extension, 'mime':mime }
            elif extension == "wmv" or extension == "asf":
                wm = wm + "<a href='%(url)s' target='_blank'>%(width)sx%(height)s</a> %(filetype)s (%(mime)s) <br/>" % { 'url':url, 'width':width, 'height':height,'filetype':extension, 'mime':mime }
            else:
                other = other + "<a href='%(url)s' target='_blank'>%(width)sx%(height)s</a> %(filetype)s (%(mime)s) <br/>" % { 'url':url, 'width':width, 'height':height,'filetype':extension, 'mime':mime }

    if len(wm) > 0:
        wm_links = "<tr><td>Windows Media:</td><td>%s</td></tr>" % wm
    if len(flv) > 0:
        flv_links = "<tr><td>Flash Media:</td><td>%s</td></tr>" % flv
    if len(other) > 0:
        other_links = "<tr><td>Other Media:</td><td>%s</td></tr>" % other

    out = """
<table class="%(download_movie_table_class)s">
 <tr>
  <td colspan="2"><strong>%(additional_links_text)s</strong></td>
 </tr>
%(flv_links)s
%(wm_links)s
%(other_links)s
</table>
""" % { 'additional_links_text':_("Download Movie"), 'flv_links':flv_links, 'wm_links':wm_links, 'other_links':other_links, 'download_movie_table_class':download_movie_table_class }
    return out


def escape_values(bfo):
    """
    Called by BibFormat in order to check if output of this element
    should be escaped.
    """
    return 0
def get_files(bfo):
    """
    Returns the files available for the given record.
    Returned structure is a list of tuples (parsed_urls, old_versions, additionals):
    """
    _ = gettext_set_language(bfo.lang)

    urls = bfo.fields("8564_")
    bibarchive = BibRecDocs(bfo.recID)

    files = []
    path_pattern ="(fullpath=(.+))"
    name_pattern ="(fullname=(.+))"
    url_pattern ="(url=(.+))"
    for f in bibarchive.list_latest_files():
        # Parse through the contents of the bib doc and extract what we are interested in
        path = re.search( path_pattern, str(f) ).group(2)
        name = re.search( url_pattern, str(f) ).group(2)
        url = re.search( url_pattern, str(f) ).group(2)
        extension = re.search( "(.)+\.(.+)", name ).group(2)
        filename, realname = unicodeFilename(path), path
        parser = createParser(filename, realname)
        if not parser:
            print >>stderr, "Unable to parse file"
        try:
            metadata = extractMetadata(parser)
        except HachoirError, err:
            print "Metadata extraction error: %s" % unicode(err)
            metadata = None
        # We do it this way because of the different file formats. some can contain multiple video streams
        text = '\n'.join(metadata.exportPlaintext())
        width = int(re.search("Image\swidth\:\s(\d+)", text).group(1))
        height = int(re.search("Image\sheight\:\s(\d+)", text).group(1))
        mime = str(re.search("MIME\stype\:\s(.+)", text).group(1))
        streamtype = re.search("(.+)\/", mime).group(1)
        files.append( [name, path, url, width, height, streamtype, extension, mime] )
    return files   
