"""
This function, get_issue_xml_records, will get the list of meetings from 
an indico server and put them into a record for display later
in the meetings widget
"""
from invenio.webjournal_utils import \
     get_xml_from_config
from invenio.config import CFG_SITE_URL
from invenio.bibformat_engine import BibFormatObject
from invenio.search_engine import search_pattern
from invenio.webjournal_utils import \
     parse_url_string
from xml.dom import minidom
from invenio.messages import gettext_set_language

def format(bfo, max_entries=0, show_all = "false", displayCategories='false',meetingCategoryClass=''):
    """
    The function called by Invenio to get the meetings of the month
    @max_entries - the number of meetings to display in the sidebar, before
                 a link to "see all" is displayed
    @show_all - whether to show all of the entries, regardless of whether it 
                 exceeds the max_entries value
    """
    args = parse_url_string(bfo.user_info['uri'])
    journal_name = args["journal_name"]
    issue = args["issue"]
    ln = args["ln"]

    config = { 'max_entries': max_entries, 'show_all': show_all, 'issue': issue, 'journal': journal_name, \
        'meetingCategoryClass':meetingCategoryClass, 'displayCategories':displayCategories }
    return get_issue_xml_records( journal_name, issue, config, ln )

def get_issue_xml_records( journal_name, issue, config, ln ):
    """
    Generate the actual HTML describing the meetings of the month
    """
    _ = gettext_set_language(ln)
    if config['max_entries'] == 0:
        try:
            config['max_entries'] = int(get_xml_from_config(["controller/meetings/display_num_meetings"], journal_name)['controller/meetings/display_num_meetings'][0])

        except:
            config['max_entries'] = 5
    xml_doc_type = get_xml_from_config(["controller/meetings/record_type"], journal_name)['controller/meetings/record_type'][0]
    indico_category_names = get_xml_from_config(["controller/meetings/indico_category_names"], journal_name)['controller/meetings/indico_category_names'][0].split(';')
    xml_records = search_pattern(p='773__t:%s and 773__n:%s and 980__a:%s not 980__c:DELETED' % (journal_name, issue, xml_doc_type ) ).tolist()

    category_names = {}
    for pair in indico_category_names:
        category_names[pair.split('=')[0]] = pair.split('=')[1]
#        name = pair.split('=')[0]
#        value = pair.split('=')[1]
#        if name.lower() == category.lower():
#            combo_value = value
#            break

    #If we don't find any records, return empty string
    if len(xml_records) == 0:
        the_result = "<ul><li><i>" + _('No record found for this month.') + "</i></li></ul>"
        return the_result

    dates = issue.split("/")
    the_month = str(int(dates[0]) - 1)
    the_year = str(dates[1])

    if the_month == str(0):
        the_month = str(12)
        the_year = str( int(the_year) - 1 )

    html = ""
    all_entries = ""
    full_html = ""
    entry_count = 0
    for rec in xml_records:
        temp_rec = BibFormatObject( rec )
        try:
            # Sort of a hack because we cannot reliably eliminate all &amp;s
            # if the record has been modified vs generated from the admin interface
            temp_str = temp_rec.field('520__a').replace('&amp;','&')
            temp_str = temp_str.replace('&','&amp;')
            rec_xml = minidom.parseString( temp_str )
        except:
            html += _("Error parsing XML for record") + " %i" % rec
            continue
        categories = rec_xml.getElementsByTagName("Indico_Meetings")
        for category in categories:
            category_id = category.getElementsByTagName("category_id")[0].firstChild.toxml()
            meetings = category.getElementsByTagName("meeting")
            if len(meetings) < 1:
                continue
            full_html += "<strong>%s</strong><ul>" % category_names[category_id]
            for meeting in meetings:
                entry = "<li>"
                try:
                    start_date = meeting.getElementsByTagName("start_date")[0].firstChild.toxml()
                except:
                    start_date = ""
                try:
                    end_date = meeting.getElementsByTagName("end_date")[0].firstChild.toxml()
                except:
                    end_date = ""
                if start_date != end_date:
                    entry += start_date + " to " + end_date + " - "
                else:
                    entry += start_date + " - "

                date_parts = start_date.split("-")
                the_month = str(int(dates[0]) - 1)
                the_year = str(dates[1])
                if the_month == str(0):
                    the_month = str(12)
                    the_year = str( int(the_year) - 1 )
                if int(date_parts[1]) != int(the_month):
                    continue
                try:
                    title = meeting.getElementsByTagName("title")[0].firstChild.toxml()
                except:
                    title = ""
                try:
                    url = meeting.getElementsByTagName("url")[0].firstChild.toxml()
                except:
                    url = "#"
                if (title != ""):
                    entry += '<strong><a href="%s">%s</a></strong>' % (url, title)
                try:
                    meeting_category = meeting.getElementsByTagName("category")[0].firstChild.toxml()
                except:
                    meeting_category = ""
                if str(config['displayCategories']).lower() == 'true':
                    entry += "<span class='%s'>%s</span>" % (config['meetingCategoryClass'], meeting_category)
                entry += "</li>"
#                all_entries += entry
                full_html += entry
                if entry_count < config['max_entries']:
                    html += entry
                entry_count += 1
            full_html += "</ul>"

    if entry_count > config['max_entries']:
        html += "<a href='" + CFG_SITE_URL + "/journal/meetings?name=%s&issue_year=%s&issue_number=%02d' > %s... </a>" % ( journal_name, issue.split("/")[1], int( issue.split("/")[0] ), _("See more") )
    html = '<ul>' + html + '</ul>'
    if entry_count == 0:
        return  "<ul><li><i>" + _("No meetings found for this month") + "</i></li></ul>"

    if config['show_all'].lower() == "true":
#        return '<ul>'+all_entries+'</ul>'
        return full_html.encode('utf-8')
    else:
        return html.encode('utf-8')


def escape_values(bfo):
    """
    Called by BibFormat in order to check if output of this element
    should be escaped.
    """
    return 0

