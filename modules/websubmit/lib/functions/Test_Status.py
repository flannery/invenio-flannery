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

   ## Description:   function Test_Status
   ##                This function checks whether the document is still waiting
   ##             for approval or not.
   ## Author:         T.Baron
   ##
   ## PARAMETERS:    -

from invenio.dbquery import run_sql
from invenio.websubmit_config import InvenioWebSubmitFunctionStop

def Test_Status(parameters, curdir, form, user_info=None):
    """
    This function checks whether the considered document has been
    requested for approval and is still waiting for approval. It also
    checks whether the password stored in file 'password' of the
    submission directory corresponds to the password associated with
    the document.
    """
    global rn
    res = run_sql("SELECT status, access FROM sbmAPPROVAL WHERE rn=%s", (rn,))
    if len(res) == 0:
        raise InvenioWebSubmitFunctionStop(printNotRequested(rn))
    else:
        if res[0][0] == "approved":
            raise InvenioWebSubmitFunctionStop(printApproved(rn))
        elif res[0][0] == "rejected":
            raise InvenioWebSubmitFunctionStop(printRejected(rn))
    return ""

def printNotRequested(rn):
    t="""
<SCRIPT>
   document.forms[0].action="/submit";
   document.forms[0].curpage.value = 1;
   document.forms[0].step.value = 0;
   user_must_confirm_before_leaving_page = false;
   document.forms[0].submit();
   alert('The document %s has never been asked for approval.\\nAnyway, you can still choose another document if you wish.');
</SCRIPT>""" % rn
    return t

def printApproved(rn):
    t="""
<SCRIPT>
   document.forms[0].action="/submit";
   document.forms[0].curpage.value = 1;
   document.forms[0].step.value = 0;
   user_must_confirm_before_leaving_page = false;
   document.forms[0].submit();
   alert('The document %s has already been approved.\\nAnyway, you can still choose another document if you wish.');
</SCRIPT>""" % rn
    return t

def printRejected(rn):
    t="""
<SCRIPT>
   document.forms[0].action="/submit";
   document.forms[0].curpage.value = 1;
   document.forms[0].step.value = 0;
   user_must_confirm_before_leaving_page = false;
   document.forms[0].submit();
   alert('The document %s has already been rejected.\\nAnyway, you can still choose another document if you wish.');
</SCRIPT>""" % rn
    return t

