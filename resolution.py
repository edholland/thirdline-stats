#!/usr/bin/env python
from jira.config import get_jira
import dateutil.parser as dp
import datetime as dt
import numpy as np
from flask import Flask
app = Flask(__name__)

PERCENTILE = 70
PROJECT = 'PROB'
THRESHOLD_OPEN = 5
THRESHOLD_NEW = 15
THRESHOLD_AGE = 250
PERIOD = 28

class gw_jira:
    def __init__(self):
        # Use config.ini, section = jira to provide server details
        # must contain user, pass, and server settings
        self.jira = get_jira(profile='jira')
        self.components = [co.name for co in self.jira.project_components(self.jira.project(PROJECT))]
        # This is the slow step, so we get everything and do the filtering ourselves
        self.issues = self.jira.search_issues('project=%s and component is not empty' % PROJECT, maxResults=2000, fields='created,customfield_10504,components')

    # Methods for calculating age of issues
    def days_old(self, issue):
        return (dt.datetime.now() - dp.parse(issue.fields.created, ignoretz=True)).days
    def hours_res(self, issue):
        return (dp.parse(issue.fields.customfield_10504) - dp.parse(issue.fields.created, ignoretz=True)).total_seconds()/(60*60)

    # Methods for filtering issues
    def filter_between(self, i, offset, period=PERIOD):
        return (self.days_old(i) > offset and self.days_old(i) < period+offset)
    
    # Methods for extracting types of issues
    def get_comp(self):
        return [ i for i in self.issues if i.fields.components[0].name in self.co ]
    def get_open(self):
        return [ i for i in self.get_comp() if not i.fields.customfield_10504 ]
    def get_resolved(self):
        return [ i for i in self.get_comp() if i.fields.customfield_10504 ]
    def get_prev_resolved(self, offset):
        return [ i for i in self.get_comp() if i.fields.customfield_10504 and self.filter_between(i, offset)]
    def get_new(self):
        return [ i for i in self.get_comp() if self.filter_between(i, 0)]

    # Methods for calculating stats from lists of issues
    def percentile(self, list):
        if len(list):
            return np.percentile([ round(self.hours_res(i), 1) for i in list ], PERCENTILE)
        return '-'

    # Methods for outputting results
    def format_line_html(self):
        output = ['<tr>']
        results = [self.co, len(self.get_open()), len(self.get_prev_resolved(0)), self.percentile(self.get_prev_resolved(0)), self.percentile(self.get_resolved()), len(self.get_new()), len(self.get_comp())]
        compare = ['', THRESHOLD_OPEN, len(self.get_prev_resolved(PERIOD)), self.percentile(self.get_resolved()),THRESHOLD_AGE, THRESHOLD_NEW, 1]
        output.append( self.table_cell(results[0]) ) # Headers
        output.append( self.table_cell(results[1], (results[1] > compare[1]) ) ) # Open
        output.append( self.table_cell(results[2], ((results[2] < compare[2]) and (results[2] > results[4])) ) ) # Resolved
        output.append( self.table_cell(results[3], ( ((results[3] > compare[3]) or (results[3] > compare[4])) and (results[3] != '-') ) ) ) # Percentile - Current
        output.append( self.table_cell(results[4], ((results[4] > compare[4]) and (results[4] != '-')) ) ) # Percentile - All time
        output.append( self.table_cell(results[5], (results[5] > compare[5]) ) ) # New
        output.append( self.table_cell(results[6], 0 ) ) # All
        output.append('</tr>')
        return ' '.join(output)

    def table_cell(self, value, func=None):
        ret = "<td align='center'"
        if func == 0:
            ret += " style='background-color:%s'> %s" % ('Green', value)
        elif func == 1:
            ret += " style='background-color:%s'> %s" % ('Red', value)
        else:
            ret += ">%s" % value
        ret += "</td>"
        return ret

@app.route('/')
def stats():
    jira = gw_jira()
    output = ['<!DOCTYPE HTML><html><head><title>Thirdline Stats</title></head><body style="background-color: Black">']
    output.append("<table width='100%' border='0' cellspacing='5' cellpadding='5' style='font-family:\"Arial Black\", Gadget, sans-serif; font-size: 36px; color: White; background-color: Black'><tr><th></th><th>Open</th><th>Resolved</th><th> Current " + str(PERCENTILE) + "<sup>th</sup>ile</th><th> All " + str(PERCENTILE) + "<sup>th</sup>ile</th><th>New</th><th>All</th></tr>")
    for co in jira.components:
        jira.co = co
        output.append( jira.format_line_html() )
    output.append("</table></body></html>")
    return "\n".join(output)

if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True)
    #print stats()
