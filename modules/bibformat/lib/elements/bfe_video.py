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




def format(bfo, style, license_key='', show_fullscreen='true', show_mute='true',show_volume='true',show_time='true', auto_buffer='true', auto_play='false'):
    """
    This is the default format for formatting video full text links.

    @param license_key: the key for FlowPlayer for the site Invenio is hosted on
        --The license keys work for *.domain.com that they are registered to
    @param show_fullscreen: 
    @param show_icons: if 'yes', print icons for fulltexts
    """
    _ = gettext_set_language(bfo.lang)

    out = ''
    # Retrieve files
#    a = BibDoc(recid="39", docname="ilc_animation_540x360.asf;1")
#    return a.get_base_dir()
    # [name, path, url, width, height, mime, extension]

#    return get_files(bfo)

    files = get_files(bfo)
    smallest = { 'width':None, 'height':None, 'url':None }
    for fileinfo in files:
        (name, path, url, width, height, streamtype, extension, mime) = fileinfo
        if streamtype == "video" and extension == "flv":
            if width <= smallest['width'] and height <= smallest['height']:
                smallest = { 'width': width, 'height':height, 'url': url }
            if smallest['width'] == None:
                smallest = { 'width': width, 'height':height, 'url': url }

    ratio = float(smallest['height']) / float(smallest['width'])
    if smallest['width'] > 600:
        smallest['width'] = 600
    if smallest['height'] > 480:
        smallest['height'] = int(float(600) * float(ratio))

    out = """
<div class="player" id="player" style="width:%(width)spx;height:%(height)spx;background-color:#d4d4d4;margin:10px;" > 
</div> 
<script>
    flowplayer("player", {src:"/img/flowplayer.commercial-3.2.2.swf" }, 
       {
          key:"%(license_key)s", 
          logo: {
            url: '/img/ilc_logo_small.png',
            fullscreenOnly: true,
            opacity: 0
           },
           // gradually show on mouseover
           onMouseOver: function() {
               this.getPlugin("logo").fadeTo(0.5, 1000);
           },
           // gradually hide on mouseout
           onMouseOut: function() {
               this.getPlugin("logo").fadeTo(0, 1000);
           },
           clip: {
               url:"%(url)s",
               autoPlay: %(auto_play)s,
               autoBuffering: %(auto_buffer)s,
               scale:'fit',
               onBegin: function () {
                   // make play button (re)appear
                   this.getPlugin("play").css({opacity: 1});
               },
               onFinish: function () {
                   // hide play again button
                   this.getPlugin("play").css({opacity: 0});
               }
           },
          plugins: { 
              controls:{ fullscreen: true, volume:true, time:true, mute:false, backgroundColor:'#01114A', backgroundGradient: 'low', buttonColor:'#FFFFFF', buttonOverColor:'#809000' } 
          } } );
</script>
    """ % {'width':smallest['width'],'height':smallest['height'],'url':smallest['url'], 'show_fullscreen':show_fullscreen, 'show_mute':show_mute, 'show_volume':show_volume, 'show_time':show_time, 'license_key':license_key, 'auto_buffer':auto_buffer,'auto_play':auto_play }

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



_RE_SPLIT = re.compile(r"\d+|\D+")
def sort_alphanumerically(elements):
    elements = [([not token.isdigit() and token or int(token) for token in _RE_SPLIT.findall(element)], element) for element in elements]
    elements.sort()
    return [element[1] for element in elements]
