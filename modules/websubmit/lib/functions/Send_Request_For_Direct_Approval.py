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

   ## Description:   function Send_Approval_Request
   ##                This function sends an email to the referee asking him/her
   ##             to approve/reject a document
   ## Author:         T.Baron
   ## PARAMETERS:    directory: parameter to the link manager program
   ##                addressesDAM: address of the referee(s)
   ##             categformatDAM: variable needed to extract the category
   ##                        of the document and use it to derive the
   ##                address.
   ##             authorfile: name of the file containing the author list
   ##             titleFile: name of the file containing the title

import os
import re

from invenio.config import \
     CFG_SITE_ADMIN_EMAIL, \
     CFG_SITE_NAME, \
     CFG_SITE_URL, \
     CFG_SITE_SUPPORT_EMAIL
from invenio.dbquery import run_sql
from invenio.access_control_admin import acc_get_role_users,acc_get_role_id
from invenio.websubmit_config import CFG_WEBSUBMIT_COPY_MAILS_TO_ADMIN
from invenio.mailutils import send_email

def Send_Request_For_Direct_Approval(parameters, curdir, form, user_info=None):
    """
    This function sends an email to the referee asking him/her to
    approve/reject a document

    Parameters:

       * directory: parameter to the link manager program

       * addressesDAM: address of the referee(s)

       * categformatDAM: variable needed to extract the category of
                         the document and use it to derive the
                         address.

       * authorfile: name of the file containing the author list

       * titleFile: name of the file containing the title
    """
    global rn,sysno
    # variables declaration
    doctype = re.search(".*/([^/]*)/([^/]*)/[^/]*$",curdir).group(2)
    FROMADDR = '%s Submission Engine <%s>' % (CFG_SITE_NAME,CFG_SITE_SUPPORT_EMAIL)
    otheraddresses = parameters['addressesDAM']
    categformat = parameters['categformatDAM']
    # retrieve category
    categformat = categformat.replace("<CATEG>","([^-]*)")
    categs = re.match(categformat,rn)
    if categs is not None:
        category = categs.group(1)
    else:
        category = "unknown"
    # create TI
    if os.path.exists("%s/date" % curdir):
        fp = open("%s/date" % curdir, "r")
        date = fp.read()
        fp.close()
    else:
        date = ""
    if os.path.exists("%s/%s" % (curdir,parameters['titleFile'])):
        fp = open("%s/%s" % (curdir,parameters['titleFile']),"r")
        title = fp.read()
        fp.close()
        title = title.replace("\n","")
    else:
        title = ""
    title += " - %s" % date
    # create AU
    if os.path.exists("%s/%s" % (curdir,parameters['authorfile'])):
        fp = open("%s/%s" % (curdir,parameters['authorfile']), "r")
        author = fp.read()
        fp.close()
    else:
        author = ""
    # we get the referee password
    #sth = run_sql("SELECT access FROM sbmAPPROVAL WHERE rn=%s", (rn,))
    #if len(sth) >0:
        #access = sth[0][0]
    # Build referee's email address
    refereeaddress = ""
    # Try to retrieve the publication committee chair's email from the role database
    for user in acc_get_role_users(acc_get_role_id("projectleader_%s_%s" % (doctype,category))):
        refereeaddress += user[1] + ","
    # And if there are general referees
    for user in acc_get_role_users(acc_get_role_id("projectleader_%s_*" % doctype)):
        refereeaddress += user[1] + ","
    refereeaddress = re.sub(",$","",refereeaddress)
    # Creation of the mail for the referee
    addresses = ""
    if refereeaddress != "":
        addresses = refereeaddress + ","
    if otheraddresses != "":
        addresses += otheraddresses
    else:
        addresses = re.sub(",$","",addresses)
    title_referee = "Request for direct approval of %s" % rn
    mail_referee = "The document %s has been asked direct approval to the %s Server..\nYour approval is requested on it.\n\n" % (rn,CFG_SITE_NAME)
    mail_referee +="Title: %s\n\nAuthor(s): %s\n\n" % (title,author)
    mail_referee +="To access the document(s), select the file(s) from the location:<%s/record/%s/files/>\n\n" % (CFG_SITE_URL,sysno)
    mail_referee +="To approve/reject the document, you should go to this URL:\n<%s/publiline.py?doctype=%s&categ=%s&RN=%s>\n" % (CFG_SITE_URL,doctype,category,rn)
    mail_referee +="---------------------------------------------\nBest regards.\nThe submission team.\n"
    #Send mail to referee
    send_email(FROMADDR, addresses, title_referee, mail_referee, copy_to_admin=CFG_WEBSUBMIT_COPY_MAILS_TO_ADMIN)
    return ""
