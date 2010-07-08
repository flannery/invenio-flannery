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

"""
    This function checks to see if the submission being edited is part of 
    an already released Web Journal publication.  
    If so, deny the user the ability to modify it, unless the account
	has action 'cfgwebjournal' with parameter 'with_editor_rights'=yes
"""

__revision__ = "$Id$"

from invenio.bibformat_engine import BibFormatObject
from invenio.websubmit_config import InvenioWebSubmitFunctionStop
from invenio.webjournal_utils import get_all_released_issues
from invenio.access_control_engine import acc_authorize_action


def Check_WebJournal_Released(parameters, curdir, form, user_info=None):
    """
    Returns a string if editing the article is allowed
    Otherwise an exception is thrown.  
    """
    global sysno

    # Verify that the current article is not part of a released webjournal issue
    # sysno should contain the record id number if everything has gone smoothly
    temp_rec = BibFormatObject(sysno)
    
    """
    The article should appear in only one journal.  
    We will get that journal name and
    then we will loop through the 773__n tags in 
    case it appears in more than one issue
    """

    journal_name = temp_rec.fields('773__t')[0]
    released_issues = get_all_released_issues( journal_name )
    #The article should appear in a single journal, 
    #but may appear in multiple issues... 
    issues = temp_rec.fields('773__n')

    for issue in issues:
        if issue in released_issues:
            auth = acc_authorize_action(user_info,
                                 'cfgwebjournal',
                                 name=journal_name,
                                 with_editor_rights='yes')
            if auth[0] == 0:
                # Authorized
                return ( """
<p style="text-align:left;"><span style='color:red; font-weight: bold; font-size:1.85em;'> Warning:</span> <br/> 
<em>This document has already been released in webjournal %s Issue %s.  However, you are authorized to make changes. <br/>
Please be aware any changes will affect the already released issues.<br/>
If you do make changes, pay attention to the 'Status' in the upper left. If offline is selected, the DRAFT keyword will be appended to the 980_a tag (collection) of this document.
</em></p>



""" % ( journal_name, issue ) )
            else:
                # Not Authorized 
                raise InvenioWebSubmitFunctionStop( 
                    "Error - you cannot modify this document because it is part of an already published Issue (%s) in (%s) " \
                        % ( issue, journal_name ) 
                    )
    #Otherwise the article remains unpublished, 
    #continue with the modifications.  
    return ""

