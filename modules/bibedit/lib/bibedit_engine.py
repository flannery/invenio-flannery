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

# pylint: disable-msg=C0103
"""CDS Invenio BibEdit Engine."""

__revision__ = "$Id"

from invenio.bibedit_config import CFG_BIBEDIT_AJAX_RESULT_CODES, \
    CFG_BIBEDIT_JS_CHECK_SCROLL_INTERVAL, CFG_BIBEDIT_JS_HASH_CHECK_INTERVAL, \
    CFG_BIBEDIT_JS_CLONED_RECORD_COLOR, \
    CFG_BIBEDIT_JS_CLONED_RECORD_COLOR_FADE_DURATION, \
    CFG_BIBEDIT_JS_NEW_ADD_FIELD_FORM_COLOR, \
    CFG_BIBEDIT_JS_NEW_ADD_FIELD_FORM_COLOR_FADE_DURATION, \
    CFG_BIBEDIT_JS_NEW_CONTENT_COLOR, \
    CFG_BIBEDIT_JS_NEW_CONTENT_COLOR_FADE_DURATION, \
    CFG_BIBEDIT_JS_NEW_CONTENT_HIGHLIGHT_DELAY, \
    CFG_BIBEDIT_JS_STATUS_ERROR_TIME, CFG_BIBEDIT_JS_STATUS_INFO_TIME, \
    CFG_BIBEDIT_JS_TICKET_REFRESH_DELAY, CFG_BIBEDIT_MAX_SEARCH_RESULTS, \
    CFG_BIBEDIT_TAG_FORMAT, CFG_BIBEDIT_AJAX_RESULT_CODES_REV

from invenio.bibedit_dblayer import get_name_tags_all, reserve_record_id, \
    get_related_hp_changesets, get_hp_update_xml, delete_hp_change, \
    get_record_last_modification_date, get_record_revision_author, \
    get_marcxml_of_record_revision, delete_related_holdingpen_changes

from invenio.bibedit_utils import cache_exists, cache_expired, \
    create_cache_file, delete_cache_file, get_bibrecord, \
    get_cache_file_contents, get_cache_mtime, get_record_templates, \
    get_record_template, latest_record_revision, record_locked_by_other_user, \
    record_locked_by_queue, save_xml_record, touch_cache_file, \
    update_cache_file_contents, get_field_templates, get_marcxml_of_revision, \
    revision_to_timestamp, timestamp_to_revision, \
    get_record_revision_timestamps, record_revision_exists

from invenio.bibrecord import create_record, print_rec, record_add_field, \
    record_add_subfield_into, record_delete_field, \
    record_delete_subfield_from, \
    record_modify_subfield, record_move_subfield, record_extract_oai_id,  \
    create_field, record_replace_field, record_move_fields, \
    record_get_subfields, record_modify_controlfield
from invenio.config import CFG_BIBEDIT_PROTECTED_FIELDS, CFG_CERN_SITE, \
    CFG_SITE_URL
from invenio.search_engine import record_exists, search_pattern, get_record
from invenio.webuser import session_param_get, session_param_set
from invenio.bibcatalog import bibcatalog_system
from invenio.bibformat import format_record
from invenio.webpage import page

import re
import difflib
import zlib
import sys
if sys.hexversion < 0x2060000:
    try:
        import simplejson as json
        simplejson_available = True
    except ImportError:
        # Okay, no Ajax app will be possible, but continue anyway,
        # since this package is only recommended, not mandatory.
        simplejson_available = False
else:
    import json
    simplejson_available = True

import invenio.template
bibedit_templates = invenio.template.load('bibedit')

re_revdate_split = re.compile('^(\d\d\d\d)(\d\d)(\d\d)(\d\d)(\d\d)(\d\d)')

def get_empty_fields_templates():
    """
    Returning the templates of empty fields :
    - an empty data field
    - an empty control field
    """
    return [{
                "name": "Empty field",
                "description": "The data field not containing any information filled in",
                "tag" : "",
                "ind1" : "",
                "ind2" : "",
                "subfields" : [("","")],
                "isControlfield" : False
            },{
                "name" : "Empty control field",
                "description" : "The controlfield not containing any data or tag description",
                "isControlfield" : True,
                "tag" : "",
                "value" : ""
            }]

def get_available_fields_templates():
    """
    A method returning all the available field templates
    Returns a list of descriptors. Each descriptor has
    the same structure as a full field descriptor inside the
    record
    """
    templates = get_field_templates()
    result = get_empty_fields_templates()
    for template in templates:
        tplTag = template[3].keys()[0]
        field = template[3][tplTag][0]

        if (field[0] == []):
        # if the field is a controlField, add different structure
            result.append({
                    "name" : template[1],
                    "description" : template[2],
                    "isControlfield" : True,
                    "tag" : tplTag,
                    "value" : field[3]
                })
        else:
            result.append({
                    "name": template[1],
                    "description": template[2],
                    "tag" : tplTag,
                    "ind1" : field[1],
                    "ind2" : field[2],
                    "subfields" : field[0],
                    "isControlfield" : False
                    })
    return result

def perform_request_init(uid, ln, req, lastupdated):
    """Handle the initial request by adding menu and JavaScript to the page."""
    errors   = []
    warnings = []
    body = ''

    # Add script data.
    record_templates = get_record_templates()
    record_templates.sort()
    tag_names = get_name_tags_all()
    protected_fields = ['001']
    protected_fields.extend(CFG_BIBEDIT_PROTECTED_FIELDS.split(','))
    history_url = '"' + CFG_SITE_URL + '/admin/bibedit/bibeditadmin.py/history"'
    cern_site = 'false'

    if not simplejson_available:
        title = 'Record Editor'
        body = '''Sorry, the record editor cannot operate when the
                `simplejson' module is not installed.  Please see the INSTALL
                file.'''
        return page(title       = title,
                    body        = body,
                    errors      = [],
                    warnings    = [],
                    uid         = uid,
                    language    = ln,
                    navtrail    = "",
                    lastupdated = lastupdated,
                    req         = req)


    if CFG_CERN_SITE:
        cern_site = 'true'
    data = {'gRECORD_TEMPLATES': record_templates,
            'gTAG_NAMES': tag_names,
            'gPROTECTED_FIELDS': protected_fields,
            'gSITE_URL': '"' + CFG_SITE_URL + '"',
            'gHISTORY_URL': history_url,
            'gCERN_SITE': cern_site,
            'gHASH_CHECK_INTERVAL': CFG_BIBEDIT_JS_HASH_CHECK_INTERVAL,
            'gCHECK_SCROLL_INTERVAL': CFG_BIBEDIT_JS_CHECK_SCROLL_INTERVAL,
            'gSTATUS_ERROR_TIME': CFG_BIBEDIT_JS_STATUS_ERROR_TIME,
            'gSTATUS_INFO_TIME': CFG_BIBEDIT_JS_STATUS_INFO_TIME,
            'gCLONED_RECORD_COLOR':
                '"' + CFG_BIBEDIT_JS_CLONED_RECORD_COLOR + '"',
            'gCLONED_RECORD_COLOR_FADE_DURATION':
                CFG_BIBEDIT_JS_CLONED_RECORD_COLOR_FADE_DURATION,
            'gNEW_ADD_FIELD_FORM_COLOR':
                '"' + CFG_BIBEDIT_JS_NEW_ADD_FIELD_FORM_COLOR + '"',
            'gNEW_ADD_FIELD_FORM_COLOR_FADE_DURATION':
                CFG_BIBEDIT_JS_NEW_ADD_FIELD_FORM_COLOR_FADE_DURATION,
            'gNEW_CONTENT_COLOR': '"' + CFG_BIBEDIT_JS_NEW_CONTENT_COLOR + '"',
            'gNEW_CONTENT_COLOR_FADE_DURATION':
                CFG_BIBEDIT_JS_NEW_CONTENT_COLOR_FADE_DURATION,
            'gNEW_CONTENT_HIGHLIGHT_DELAY':
                CFG_BIBEDIT_JS_NEW_CONTENT_HIGHLIGHT_DELAY,
            'gTICKET_REFRESH_DELAY': CFG_BIBEDIT_JS_TICKET_REFRESH_DELAY,
            'gRESULT_CODES': CFG_BIBEDIT_AJAX_RESULT_CODES
            }
    body += '<script type="text/javascript">\n'
    for key in data:
        body += '    var %s = %s;\n' % (key, data[key])
    body += '    </script>\n'

    # Adding the information about field templates
    fieldTemplates = get_available_fields_templates()
    body += "<script>\n" + \
            "   var fieldTemplates = %s\n"%(json.dumps(fieldTemplates), ) + \
            "</script>\n"
    # Add scripts (the ordering is NOT irrelevant).
    scripts = ['jquery.min.js', 'jquery.effects.core.min.js',
               'jquery.effects.highlight.min.js', 'jquery.autogrow.js',
               'jquery.jeditable.mini.js', 'jquery.hotkeys.min.js', 'json2.js',
               'bibedit_display.js', 'bibedit_engine.js', 'bibedit_keys.js',
               'bibedit_menu.js', 'bibedit_holdingpen.js', 'marcxml.js',
               'bibedit_clipboard.js']

    for script in scripts:
        body += '    <script type="text/javascript" src="%s/js/%s">' \
            '</script>\n' % (CFG_SITE_URL, script)

    # Build page structure and menu.
    rec = create_record(format_record(235, "xm"))[0]
    oaiId = record_extract_oai_id(rec)

    body += bibedit_templates.menu()
    body += '    <div id="bibEditContent"></div>\n'

    return body, errors, warnings

def get_xml_comparison(header1, header2, xml1, xml2):
    """
    Return diffs of two MARCXML records.
    """
    return "".join(difflib.unified_diff(xml1.splitlines(1),
        xml2.splitlines(1), header1, header2))

def get_marcxml_of_revision_id(recid, revid):
    """
    Return MARCXML string with corresponding to revision REVID
    (=RECID.REVDATE) of a record.  Return empty string if revision
    does not exist.
    """
    res = ""
    job_date = "%s-%s-%s %s:%s:%s" % re_revdate_split.search(revid).groups()
    tmp_res = get_marcxml_of_record_revision(recid, job_date)
    if tmp_res:
        for row in tmp_res:
            res += zlib.decompress(row[0]) + "\n"
    return res

def perform_request_compare(req, ln, recid, rev1, rev2):
    """Handle a request for comparing two records"""
    body = ""
    errors = []
    warnings = []

    if (not record_revision_exists(recid, rev1)) or (not record_revision_exists(recid, rev2)):
        body = "The requested record revision does not exist !"
    else:
        xml1 = get_marcxml_of_revision_id(recid, rev1)
        xml2 = get_marcxml_of_revision_id(recid, rev2)
        fullrevid1 = "%i.%s" %(recid, rev1)
        fullrevid2 = "%i.%s" %(recid, rev2)
        comparison = bibedit_templates.clean_value(
            get_xml_comparison(fullrevid1, fullrevid2, xml1, xml2),
            'text').replace('\n', '<br />\n           ')
        job_date1 = "%s-%s-%s %s:%s:%s" % re_revdate_split.search(rev1).groups()
        job_date2 = "%s-%s-%s %s:%s:%s" % re_revdate_split.search(rev2).groups()
        body += bibedit_templates.history_comparebox(ln, job_date1,
                                                 job_date2, comparison)
    return body, errors, warnings

def perform_request_newticket(recid, uid):
    """create a new ticket with this record's number
    @param recid: record id
    @param uid: user id
    @return: (error_msg, url)

    """
    t_id = bibcatalog_system.ticket_submit(uid, "", recid, "")
    t_url = ""
    errmsg = ""
    if t_id:
        #get the ticket's URL
        t_url = bibcatalog_system.ticket_get_attribute(uid, t_id, 'url_modify')
    else:
        errmsg = "ticket_submit failed"
    return (errmsg, t_url)

def perform_request_ajax(req, recid, uid, data):
    """Handle Ajax requests by redirecting to appropriate function."""
    response = {}
    request_type = data['requestType']

    # Call function based on request type.
    if request_type == 'searchForRecord':
        # Search request.
        response.update(perform_request_search(data))
    elif request_type in ['changeTagFormat']:
        # User related requests.
        response.update(perform_request_user(req, request_type, recid, data))
    elif request_type in ('getRecord', 'submit', 'cancel', 'newRecord',
        'deleteRecord', 'deleteRecordCache', 'prepareRecordMerge', 'revert'):
        # 'Major' record related requests.
        response.update(perform_request_record(req, request_type, recid, uid,
                                               data))
    elif request_type in ('addField', 'addSubfields', 'modifyContent',
                          'moveSubfield', 'deleteFields', 'moveField', 'modifyField',
                          'overrideChangesList', 'removeChange', 'disableHpChange',
                          'desactivateHoldingPenChangeset'):
        # Record updates.
        cacheMTime = data['cacheMTime']
        if data.has_key('changeApplied'):
            hpChangeApplied = data['changeApplied'] # a number of the change currently visulaiosed in the interface that has been applied by this request ( to be removed )
        else:
            hpChangeApplied = -1
        response.update(perform_request_update_record(
                request_type, recid, uid, cacheMTime, data, hpChangeApplied))

    elif request_type in ('getTickets'):
        # BibCatalog requests.
        response.update(perform_request_bibcatalog(request_type, recid, uid))
    elif request_type in ('getHoldingPenUpdates'):
        response.update(perform_request_holdingpen(request_type, recid))

    elif request_type in ('getHoldingPenUpdateDetails', 'deleteHoldingPenChangeset'):
        updateId = data['changesetNumber']
        response.update(perform_request_holdingpen(request_type, recid, updateId))
    elif request_type in ('applyBulkUpdates'):
        changes = data['value']
        cacheMTime = data['cacheMTime']
        response.update(perform_bulk_request(recid, uid, changes, cacheMTime))
    return response

def perform_request_search(data):
    """Handle search requests."""
    response = {}
    searchType = data['searchType']
    searchPattern = data['searchPattern']
    if searchType == 'anywhere':
        pattern = searchPattern
    else:
        pattern = searchType + ':' + searchPattern
    result_set = list(search_pattern(p=pattern))
    response['resultCode'] = 1
    response['resultSet'] = result_set[0:CFG_BIBEDIT_MAX_SEARCH_RESULTS]
    return response

def perform_request_user(req, request_type, recid, data):
    """Handle user related requests."""
    response = {}
    if request_type == 'changeTagFormat':
        try:
            tagformat_settings = session_param_get(req, 'bibedit_tagformat')
        except KeyError:
            tagformat_settings = {}
        tagformat_settings[recid] = data['tagFormat']
        session_param_set(req, 'bibedit_tagformat', tagformat_settings)
        response['resultCode'] = 2
    return response

def perform_request_holdingpen(request_type, recId, changeId=None):
    """
    A method performing the holdingPen ajax request. The following types of requests can be made:
       getHoldingPenUpdates - retrieving the holding pen updates pending for a given record
    """
    response = {}
    if request_type == 'getHoldingPenUpdates':
        changeSet = get_related_hp_changesets(recId)
        changes = []
        for change in changeSet:
            changes.append((str(change[0]), str(change[1])))
        response["changes"] = changes
    elif request_type == 'getHoldingPenUpdateDetails':
        # returning the list of changes related to the holding pen update
        # the format based on what the record difference xtool returns

        assert(changeId != None)
        hpContent = get_hp_update_xml(changeId)
        holdingPenRecord = create_record(hpContent[0], "xm")[0]
        databaseRecord = get_record(hpContent[1])
        response['record'] = holdingPenRecord
        response['changeset_number'] = changeId;
    elif request_type == 'deleteHoldingPenChangeset':
        assert(changeId != None)
        delete_hp_change(changeId);
    return response

def perform_bulk_request(recId, uid, changes, cacheMTime):
    """
        A method performing an AJAX call corresponding to a large number of operations
        intended to be applied together

        Parameters:

        recId :    an identifier of the record being affected by the changes.
        changes :  a list of lists of changes. The purpose of using double list is to make an
                   explicit distinction between different categories of changes.
                   Some of the changes should be performed before others because they may change the
                   data utilised by them. This would be of course possible to utilise a single list that
                   preserves the ordering. The double depth list makes the distinction much clearer.
                   A sample value :  [[], []]
        uid : the uid parameter passed as to the perform_request_update_record function
    """
    lastResponse = {}
    for changeset in changes:
        for change in changeset:
            requestType = change["requestType"]
            if  requestType in ('addField', 'addSubfields', 'modifyContent',
                          'moveSubfield', 'deleteFields', 'moveField', 'modifyField'):
#                import rpdb2; rpdb2.start_embedded_debugger('somepassword', fAllowRemote = True)

                if change.has_key('changeApplied'):
                    hpChangeApplied = int(change['changeApplied']) # a number of the change currently visulaiosed in the interface that has been applied by this request ( to be removed )
                else:
                    hpChangeApplied = -1
                lastResponse = perform_request_update_record(requestType, recId, uid, cacheMTime, change, hpChangeApplied, isBulk = True)

                cacheMTime  = lastResponse['cacheMTime'] # Next call has to use this modification time

    result = lastResponse
    result["resultCode"] = 34
    result["cacheDirty"] = True
    return result


def perform_request_record(req, request_type, recid, uid, data):
    """Handle 'major' record related requests like fetching, submitting or
    deleting a record, cancel editing or preparing a record for merging.

    """
    response = {}

    if request_type == 'newRecord':
        # Create a new record.
        new_recid = reserve_record_id()
        new_type = data['newType']
        if new_type == 'empty':
            # Create a new empty record.
            create_cache_file(recid, uid)
            response['resultCode'], response['newRecID'] = 6, new_recid

        elif new_type == 'template':
            # Create a new record from XML record template.
            template_filename = data['templateFilename']
            template = get_record_template(template_filename)
            if not template:
                response['resultCode']  = 108
            else:
                record = create_record(template)[0]
                if not record:
                    response['resultCode']  = 109
                else:
                    record_add_field(record, '001',
                                     controlfield_value=str(new_recid))
                    create_cache_file(new_recid, uid, record, True)
                    response['resultCode'], response['newRecID']  = 7, new_recid

        elif new_type == 'clone':
            # Clone an existing record (from the users cache).
            existing_cache = cache_exists(recid, uid)
            if existing_cache:
                try:
                    record = get_cache_file_contents(recid, uid)[2]
                except:
                    # if, for example, the cache format was wrong (outdated)
                    record = get_bibrecord(recid)
            else:
                # Cache missing. Fall back to using original version.
                record = get_bibrecord(recid)
            record_delete_field(record, '001')
            record_add_field(record, '001', controlfield_value=str(new_recid))
            create_cache_file(new_recid, uid, record, True)
            response['resultCode'], response['newRecID'] = 8, new_recid
    elif request_type == 'getRecord':
        # Fetch the record. Possible error situations:
        # - Non-existing record
        # - Deleted record
        # - Record locked by other user
        # - Record locked by queue
        # A cache file will be created if it does not exist.
        # If the cache is outdated (i.e., not based on the latest DB revision),
        # cacheOutdated will be set to True in the response.
        record_status = record_exists(recid)
        existing_cache = cache_exists(recid, uid)
        read_only_mode = False
        if data.has_key("inReadOnlyMode"):
            read_only_mode = data['inReadOnlyMode']

        if record_status == 0:
            response['resultCode'] = 102
        elif record_status == -1:
            response['resultCode'] = 103
        elif not read_only_mode and not existing_cache and \
                record_locked_by_other_user(recid, uid):
            response['resultCode'] = 104
        elif not read_only_mode and existing_cache and \
                cache_expired(recid, uid) and \
                record_locked_by_other_user(recid, uid):
            response['resultCode'] = 104
        elif not read_only_mode and record_locked_by_queue(recid):
            response['resultCode'] = 105
        else:
            if data.get('deleteRecordCache'):
                delete_cache_file(recid, uid)
                existing_cache = False
                pending_changes = []
                disabled_hp_changes = {}
            if read_only_mode:
                if data.has_key('recordRevision'):
                    record_revision_ts = data['recordRevision']
                    record_xml = get_marcxml_of_revision(recid, record_revision_ts)
                    record = create_record(record_xml)[0]
                    record_revision = timestamp_to_revision(record_revision_ts)
                    pending_changes = []
                    disabled_hp_changes = {}
                else:
                    # a normal cacheless retrieval of a record
                    record = get_bibrecord(recid)
                    record_revision = get_record_last_modification_date(recid)
                    pending_changes = []
                    disabled_hp_changes = {}
                cache_dirty = False
                mtime = 0
            elif not existing_cache:
                record_revision, record = create_cache_file(recid, uid)
                mtime = get_cache_mtime(recid, uid)
                pending_changes = []
                disabled_hp_changes = {}
                cache_dirty = False
            else:
                try:
                    cache_dirty, record_revision, record, pending_changes, disabled_hp_changes= \
                        get_cache_file_contents(recid, uid)
                    touch_cache_file(recid, uid)
                    mtime = get_cache_mtime(recid, uid)
                    if not latest_record_revision(recid, record_revision):
                        response['cacheOutdated'] = True
                except:
                    record_revision, record = create_cache_file(recid, uid)
                    mtime = get_cache_mtime(recid, uid)
                    pending_changes = []
                    disabled_hp_changes = {}
                    cache_dirty = False

            if data['clonedRecord']:
                response['resultCode'] = 9
            else:
                response['resultCode'] = 3

            revision_author = get_record_revision_author(recid, record_revision)
            last_revision_ts = revision_to_timestamp(get_record_last_modification_date(recid))
            revisions_history = get_record_revision_timestamps(recid)

            response['cacheDirty'], response['record'], response['cacheMTime'],\
                response['recordRevision'], response['revisionAuthor'], \
                response['lastRevision'], response['revisionsHistory'], \
                response['inReadOnlyMode'], response['pendingHpChanges'], \
                response['disabledHpChanges'] = cache_dirty, record, mtime, \
                revision_to_timestamp(record_revision), revision_author, \
                last_revision_ts, revisions_history, read_only_mode, pending_changes, \
                disabled_hp_changes
            # Set tag format from user's session settings.
            try:
                tagformat_settings = session_param_get(req, 'bibedit_tagformat')
                tagformat = tagformat_settings[recid]
            except KeyError:
                tagformat = CFG_BIBEDIT_TAG_FORMAT
            response['tagFormat'] = tagformat

    elif request_type == 'submit':
        # Submit the record. Possible error situations:
        # - Missing cache file
        # - Cache file modified in other editor
        # - Record locked by other user
        # - Record locked by queue
        # - Invalid XML characters
        # If the cache is outdated cacheOutdated will be set to True in the
        # response.
        if not cache_exists(recid, uid):
            response['resultCode'] = 106
        elif not get_cache_mtime(recid, uid) == data['cacheMTime']:
            response['resultCode'] = 107
        elif cache_expired(recid, uid) and \
                record_locked_by_other_user(recid, uid):
            response['resultCode'] = 104
        elif record_locked_by_queue(recid):
            response['resultCode'] = 105
        else:
            try:
                record_revision, record, pending_changes, disabled_changes = get_cache_file_contents(recid, uid)[1:]
                xml_record = print_rec(record)
                record, status_code, list_of_errors = create_record(xml_record)
                if status_code == 0:
                    response['resultCode'], response['errors'] = 110, \
                        list_of_errors
                elif not data['force'] and \
                        not latest_record_revision(recid, record_revision):
                    response['cacheOutdated'] = True
                else:
                    save_xml_record(recid, uid)
                    response['resultCode'] = 4
            except:
                response['resultCode'] = CFG_BIBEDIT_AJAX_RESULT_CODES_REV['wrong_cache_file_format']
    elif request_type == 'revert':
        revId = data['revId']
        job_date = "%s-%s-%s %s:%s:%s" % re_revdate_split.search(revId).groups()
        revision_xml = get_marcxml_of_revision(recid, job_date)
        save_xml_record(recid, uid, revision_xml)
        if (cache_exists(recid, uid)):
            delete_cache_file(recid, uid)
        response['resultCode'] = 4

    elif request_type == 'cancel':
        # Cancel editing by deleting the cache file. Possible error situations:
        # - Cache file modified in other editor
        if cache_exists(recid, uid):
            if get_cache_mtime(recid, uid) == data['cacheMTime']:
                delete_cache_file(recid, uid)
                response['resultCode'] = 5
            else:
                response['resultCode'] = 107
        else:
            response['resultCode'] = 5

    elif request_type == 'deleteRecord':
        # Submit the record. Possible error situations:
        # - Record locked by other user
        # - Record locked by queue
        # As the user is requesting deletion we proceed even if the cache file
        # is missing and we don't check if the cache is outdated or has
        # been modified in another editor.
        existing_cache = cache_exists(recid, uid)
        pending_changes = []
        if existing_cache and cache_expired(recid, uid) and \
                record_locked_by_other_user(recid, uid):
            response['resultCode'] = 104
        elif record_locked_by_queue(recid):
            response['resultCode'] = 105
        else:
            if not existing_cache:
                record_revision, record, pending_changes, desactivated_hp_changes = create_cache_file(recid, uid)
            else:
                try:
                    record_revision, record, pending_changes, desactivated_hp_changes = get_cache_file_contents(
                        recid, uid)[1:]
                except:
                    record_revision, record, pending_changes, desactivated_hp_changes = create_cache_file(recid, uid)
            record_add_field(record, '980', ' ', ' ', '', [('c', 'DELETED')])
            update_cache_file_contents(recid, uid, record_revision, record, pending_changes, desactivated_hp_changes)
            save_xml_record(recid, uid)
            delete_related_holdingpen_changes(recid) # we don't need any changes related to a deleted record
            response['resultCode'] = 10

    elif request_type == 'deleteRecordCache':
        # Delete the cache file. Ignore the request if the cache has been
        # modified in another editor.
        if cache_exists(recid, uid) and get_cache_mtime(recid, uid) == \
                data['cacheMTime']:
            delete_cache_file(recid, uid)
        response['resultCode'] = 11

    elif request_type == 'prepareRecordMerge':
        # We want to merge the cache with the current DB version of the record,
        # so prepare an XML file from the file cache, to be used by BibMerge.
        # Possible error situations:
        # - Missing cache file
        # - Record locked by other user
        # - Record locked by queue
        # We don't check if cache is outdated (a likely scenario for this
        # request) or if it has been modified in another editor.
        if not cache_exists(recid, uid):
            response['resultCode'] = 106
        elif cache_expired(recid, uid) and \
                record_locked_by_other_user(recid, uid):
            response['resultCode'] = 104
        elif record_locked_by_queue(recid):
            response['resultCode'] = 105
        else:
            save_xml_record(recid, uid, to_upload=False, to_merge=True)
            response['resultCode'] = 12

    return response

def perform_request_update_record(request_type, recid, uid, cacheMTime, data, changeApplied, isBulk=False):
    """Handle record update requests like adding, modifying, moving or deleting
    of fields or subfields. Possible common error situations:
    - Missing cache file
    - Cache file modified in other editor
    """

    response = {}

    if not cache_exists(recid, uid):
        response['resultCode'] = 106
    elif not get_cache_mtime(recid, uid) == cacheMTime and isBulk == False:
        # In case of a bulk request, the changes are deliberately performed imemdiately one after another
        response['resultCode'] = 107
    else:
        try:
            record_revision, record, pending_changes, desactivated_hp_changes = get_cache_file_contents(recid, uid)[1:]
        except:
            response['resultCode'] = CFG_BIBEDIT_AJAX_RESULT_CODES_REV['wrong_cache_file_format']
            return response;

        if changeApplied != -1:
            pending_changes = pending_changes[:changeApplied] + pending_changes[changeApplied+1:]

        field_position_local = data.get('fieldPosition')
        if field_position_local is not None:
            field_position_local = int(field_position_local)
        if request_type == 'overrideChangesList':
            pending_changes = data['newChanges']
            response['resultCode'] = CFG_BIBEDIT_AJAX_RESULT_CODES_REV['editor_modifications_changed']
        elif request_type == 'removeChange':
            #the change is removed automatically by passing the changeApplied parameter
            response['resultCode'] = CFG_BIBEDIT_AJAX_RESULT_CODES_REV['editor_modifications_changed']
        elif request_type == 'desactivateHoldingPenChangeset':
            # the changeset has been marked as processed ( user applied it in the editor)
            # marking as used in the cache file
            # CAUTION: This function has been implemented here because logically it fits
            #          with the modifications made to the cache file. No changes are made to the
            #          Holding Pen physically. The changesets are related to the cache because
            #          we want to cancel the removal every time the cache disappears for any reason
            desactivated_hp_changes[data.get('desactivatedChangeset')] = True;
            response['resultCode'] = CFG_BIBEDIT_AJAX_RESULT_CODES_REV['disabled_hp_changeset']
        elif request_type == 'addField':
            if data['controlfield']:
                record_add_field(record, data['tag'],
                                 controlfield_value=data['value'])
                response['resultCode'] = 20
            else:
                record_add_field(record, data['tag'], data['ind1'],
                                 data['ind2'], subfields=data['subfields'],
                                 field_position_local=field_position_local)
                response['resultCode'] = 21

        elif request_type == 'addSubfields':
            subfields = data['subfields']
            for subfield in subfields:
                record_add_subfield_into(record, data['tag'], subfield[0],
                    subfield[1], subfield_position=None,
                    field_position_local=field_position_local)
            if len(subfields) == 1:
                response['resultCode'] = 22
            else:
                response['resultCode'] = 23
        elif request_type == 'modifyField': # changing the field structure
            # first remove subfields and then add new... change the indices
            subfields = data['subFields'] # parse the JSON representation of the subfields here

            new_field = create_field(subfields, data['ind1'], data['ind2']);
            record_replace_field(record, data['tag'], new_field, field_position_local = data['fieldPosition'])
            response['resultCode'] = 26
            #response['debuggingValue'] = data['subFields'];

        elif request_type == 'modifyContent':
            if data['subfieldIndex'] != None:
                record_modify_subfield(record, data['tag'],
                    data['subfieldCode'], data['value'],
                    int(data['subfieldIndex']),
                    field_position_local=field_position_local)
            else:
                record_modify_controlfield(record, data['tag'], data["value"],
                  field_position_local=field_position_local)
            response['resultCode'] = 24

        elif request_type == 'moveSubfield':
            record_move_subfield(record, data['tag'],
                int(data['subfieldIndex']), int(data['newSubfieldIndex']),
                field_position_local=field_position_local)
            response['resultCode'] = 25

        elif request_type == 'moveField':
            if data['direction'] == 'up':
                final_position_local = field_position_local-1
            else: # direction is 'down'
                final_position_local = field_position_local+1
            record_move_fields(record, data['tag'], [field_position_local],
                final_position_local)
            response['resultCode'] = 32

        elif request_type == 'deleteFields':
            to_delete = data['toDelete']
            deleted_fields = 0
            deleted_subfields = 0
            for tag in to_delete:
                # Sorting the fields in a edcreasing order by the local position !
                fieldsOrder = to_delete[tag].keys()
                fieldsOrder.sort(lambda a,b: int(b)-int(a))
                for field_position_local in fieldsOrder:
                    if not to_delete[tag][field_position_local]:
                        # No subfields specified - delete entire field.
                        record_delete_field(record, tag,
                            field_position_local=int(field_position_local))
                        deleted_fields += 1
                    else:
                        for subfield_position in \
                                to_delete[tag][field_position_local][::-1]:
                            # Delete subfields in reverse order (to keep the
                            # indexing correct).
                            record_delete_subfield_from(record, tag,
                                int(subfield_position),
                                field_position_local=int(field_position_local))
                            deleted_subfields += 1
            if deleted_fields == 1 and deleted_subfields == 0:
                response['resultCode'] = 26
            elif deleted_fields and deleted_subfields == 0:
                response['resultCode'] = 27
            elif deleted_subfields == 1 and deleted_fields == 0:
                response['resultCode'] = 28
            elif deleted_subfields and deleted_fields == 0:
                response['resultCode'] = 29
            else:
                response['resultCode'] = 30
        response['cacheMTime'], response['cacheDirty'] = \
            update_cache_file_contents(recid, uid, record_revision, record, \
                                       pending_changes, desactivated_hp_changes), \
            True

    return response

def perform_request_bibcatalog(request_type, recid, uid):
    """Handle request to BibCatalog (RT).

    """
    response = {}

    if request_type == 'getTickets':
        # Insert the ticket data in the response, if possible
        if uid:
            bibcat_resp = bibcatalog_system.check_system(uid)
            if bibcat_resp == "":
                tickets_found = bibcatalog_system.ticket_search(uid, status=['new', 'open'], recordid=recid)
                t_url_str = '' #put ticket urls here, formatted for HTML display
                for t_id in tickets_found:
                    #t_url = bibcatalog_system.ticket_get_attribute(uid, t_id, 'url_display')
                    ticket_info = bibcatalog_system.ticket_get_info(uid, t_id, ['url_display','url_close'])
                    t_url = ticket_info['url_display']
                    t_close_url = ticket_info['url_close']
                    #format..
                    t_url_str += "#"+str(t_id)+'<a href="'+t_url+'">[read]</a> <a href="'+t_close_url+'">[close]</a><br/>'
                #put ticket header and tickets links in the box
                t_url_str = "<strong>Tickets</strong><br/>"+t_url_str+"<br/>"+'<a href="new_ticket?recid='+str(recid)+'>[new ticket]<a>'
                response['tickets'] = t_url_str
                #add a new ticket link
            else:
                #put something in the tickets container, for debug
                response['tickets'] = "<!--"+bibcat_resp+"-->"
        response['resultCode'] = 31

    return response

