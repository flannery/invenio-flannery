## $Id$

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
"""Functions shared by websumit_functions"""

__revision__ = "$Id$"

from invenio.config import \
     CFG_PATH_ACROREAD, \
     CFG_PATH_CONVERT, \
     CFG_PATH_DISTILLER, \
     CFG_PATH_GUNZIP, \
     CFG_PATH_GZIP
import re
import os

def createRelatedFormats(fullpath):
    """Given a fullpath, this function extracts the file's extension and
    finds in which additional format the file can be converted and converts it.
    @param fullpath: (string) complete path to file
    Return a list of the paths to the converted files
    """
    createdpaths = []
    basedir = os.path.dirname(fullpath)
    filename = os.path.basename(fullpath)
    filename, extension = os.path.splitext(filename)
    extension = extension.lower()
    if extension == ".pdf":
        # Create PostScript
        os.system("%s -toPostScript %s" % (CFG_PATH_ACROREAD, fullpath))
        if os.path.exists("%s/%s.ps" % (basedir, filename)):
            os.system("%s %s/%s.ps" % (CFG_PATH_GZIP, basedir, filename))
            createdpaths.append("%s/%s.ps.gz" % (basedir, filename))
    if extension == ".ps":
        # Create PDF
        os.system("%s %s %s/%s.pdf" % (CFG_PATH_DISTILLER, fullpath, \
                                       basedir, filename))
        if os.path.exists("%s/%s.pdf" % (basedir, filename)):
            createdpaths.append("%s/%s.pdf" % (basedir, filename))
    if extension == ".ps.gz":
        #gunzip file
        os.system("%s %s" % (CFG_PATH_GUNZIP, fullpath))
        # Create PDF
        os.system("%s %s/%s.ps %s/%s.pdf" % (CFG_PATH_DISTILLER, basedir, \
                                             filename, basedir, filename))
        if os.path.exists("%s/%s.pdf" % (basedir, filename)):
            createdpaths.append("%s/%s.pdf" % (basedir, filename))
        #gzip file
        os.system("%s %s/%s.ps" % (CFG_PATH_GZIP, basedir, filename))
    return createdpaths

def createIcon(fullpath, iconsize):
    """Given a fullpath, this function extracts the file's extension and
    if the format is compatible it converts it to icon.
    @param fullpath: (string) complete path to file
    Return the iconpath if successful otherwise None
    """
    basedir = os.path.dirname(fullpath)
    filename = os.path.basename(fullpath)
    filename, extension = os.path.splitext(filename)
    if extension == filename:
        extension == ""
    iconpath = "%s/icon-%s.gif" % (basedir, filename)
    if os.path.exists(fullpath) and extension.lower() in ['.pdf', '.gif', '.jpg', '.jpeg', '.ps']:
        os.system("%s -scale %s %s %s" % (CFG_PATH_CONVERT, iconsize, fullpath, iconpath))
    if os.path.exists(iconpath):
        return iconpath
    else:
        return None
    
def get_dictionary_from_string(dict_string):
    """Given a string version of a "dictionary", split the string into a
       python dictionary.
       For example, given the following string:
         {'TITLE' : 'EX_TITLE', 'AUTHOR' : 'EX_AUTHOR', 'REPORTNUMBER' : 'EX_RN'}
       A dictionary in the following format will be returned:
         {
            'TITLE'        : 'EX_TITLE',
            'AUTHOR'       : 'EX_AUTHOR',
            'REPORTNUMBER' : 'EX_RN',
         }
       @param dict_string: (string) - the string version of the dictionary.
       @return: (dictionary) - the dictionary build from the string.
    """
    ## First, strip off the leading and trailing spaces and braces:
    dict_string = dict_string.strip(" {}")
    
    ## Next, split the string on commas (,) that have not been escaped
    ## So, the following string: """'hello' : 'world', 'click' : 'here'""" will be split
    ## into the following list: ["'hello' : 'world'", " 'click' : 'here'"]
    ##
    ## However, The following string: """'hello\, world' : '!', 'click' : 'here'"""
    ## will be split into: ["'hello\, world' : '!'", " 'click' : 'here'"]
    ## I.e. the comma that was escaped in the string has been kept.
    ##
    ## So basically, split on unescaped parameters at first:
    key_vals = re.split(r'(?<!\\),', dict_string)

    ## Now we should have a list of "key" : "value" terms. For each of them, check
    ## it is OK. If not in the format "Key" : "Value" (quotes are optional), discard it.
    ## As with the comma separator in the previous splitting, this one splits on any colon
    ## (:) that is not escaped by a backslash.
    final_dictionary = {}
    for key_value_string in key_vals:
        ## Split the pair apart, based on ":":
        key_value_pair = re.split(r'(?<!\\):', key_value_string)
        ## check that the length of the new list is 2:
        if len(key_value_pair) != 2:
            ## There was a problem with the splitting - pass this pair
            continue
        ## The split was made.
        ## strip white-space, single-quotes and double-quotes from around the
        ## key and value pairs:
        key_term   = key_value_pair[0].strip(" '\"")
        value_term = key_value_pair[1].strip(" '\"")

        ## Is the left-side (key) term empty?
        if len(key_term) == 0:
            continue

        ## Now, add the search-replace pair to the dictionary of search-replace terms:
        final_dictionary[key_term] = value_term
    return final_dictionary
