"""
This function, get_issue_xml_records, will get the list of meetings from 
an indico server and put them into a record for display later
in the meetings widget
"""

from invenio.webjournal_utils import \
     get_xml_from_config, \
     make_journal_url, \
     is_new_article
from invenio.webjournal_utils import parse_url_string
from invenio.config import CFG_SITE_URL
from invenio.bibformat_engine import BibFormatObject
from invenio.search_engine import search_pattern

def format(bfo, entries_to_show=3, prefix="<div class='related_articles'><strong>Past Articles</strong>", suffix="</div>"):
    args = parse_url_string(bfo.user_info['uri'])
    journal_name = args["journal_name"]
    category = args["category"]
    this_recid = args["recid"]
    this_issue = args["issue"]
    ln = args["ln"]
    topic = bfo.fields('65017a')[0]
#    collection = bfo.fields('980__a')[0]   #
    config_strings = get_xml_from_config(["record/rule"], journal_name)
    category_to_search_pattern_rules = config_strings["record/rule"]

    try:
        matching_rule = [rule.split(',', 1) for rule in \
                         category_to_search_pattern_rules \
                         if rule.split(',')[0] == category]
    except:
        return "category: %s" % category
    recids_rule = search_pattern(p=matching_rule[0][1])

    recids_topic = search_pattern(p='773__t:%s and 65017a:%s not 980__c:DELETED' % (journal_name, topic ) ).tolist()
#    recids_rule.intersection_update(recids_topic)
    recids_rule = set(recids_rule).intersection( set(recids_topic) )

    html = prefix + "<ul>"
#    if len(recids_rule) == 1:  #If we only found ourself
#        return ""
    entry_count = 0
    for record in list( recids_rule ):
        if entry_count < entries_to_show:
            if record == this_recid:
                continue
            temp_rec = BibFormatObject( record )
            issue_num = temp_rec.field('773__n')
            url = make_journal_url(bfo.user_info['uri'], {'recid':record,'ln': ln,'issue_number':issue_num.split('/')[0],'issue_year':issue_num.split('/')[1]})

            # Write out the links that are of older issues only
            issue_number1, issue_year1 = this_issue.split('/', 1)
            issue_number2, issue_year2 = issue_num.split('/', 1)

            if (int(issue_year1) > int(issue_year2)) or ( int(issue_year1)==int(issue_year2) and int(issue_number1)>int(issue_number2) ):
                entry_count += 1
                html += "<li><a href='%(href)s'>%(title)s</a> <span class='%(date_class)s'>%(issue_num)s</span></li>" % { 'title': temp_rec.field('245__a'), 'issue_num': issue_num, 'href':url, 'date_class': 'related_issue_date' }
            else:
                html += ""

    search_link = ""
    if entry_count >= entries_to_show:
#    search_url = CFG_SITE_URL + "/search?ln=en&p=773__t:%s and 65017a:%s and 980__a:%s not 980__c:DELETED" % (journal_name, topic, collection )
    # Since it searches only public collections anyway, using the 980__a tag is probably not necessary. 
        search_url = CFG_SITE_URL + "/search?ln=en&p=773__t:%s and 65017a:%s not 980__c:DELETED" % (journal_name, topic )
        search_link = "<a href='%s'>See all</a>" % search_url
    html += "</ul>" + search_link + suffix

#    html += "</ul>" + suffix
    if entry_count > 0:
        return html
    else:
        return ""

def escape_values(bfo):
    """
    Called by BibFormat in order to check if output of this element
    should be escaped.
    """
    return 0
