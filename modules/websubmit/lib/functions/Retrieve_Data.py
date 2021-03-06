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

__revision__ = "$Id$"

   ## Description:   function Get_Field
   ##                This function returns the value of the specified field
   ##             from the specified document
   ## Author:         T.Baron
   ##
   ## PARAMETERS:    fieldname: marc21 code
   ##                bibrec: system number of the bibliographic record

import string

from invenio.search_engine import search_pattern, perform_request_search, print_record

def Get_Field(fieldname,bibrec):
    """
    This function returns the value of the specified field
    from the specified document
    """
    value = string.strip(print_record(int(bibrec),'tm',[fieldname]))
    return value

