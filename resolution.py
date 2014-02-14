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
        """Get jira connection, list of components and issues"""
        # Use config.ini, section = jira to provide server details
        # must contain user, pass, and server settings
        self.jira = get_jira(profile='jira')
        self.components = [co.name for co in self.jira.project_components(self.jira.project(PROJECT))]
        # This is the slow step, so we get everything and do the filtering ourselves
        self.issues = self.jira.search_issues('project=%s and component is not empty' % PROJECT, maxResults=2000, fields='created,customfield_10504,components')

    # Methods for calculating age of issues
    def days_old(self, issue):
        """Returns number of days since issue creation"""
        return (dt.datetime.now() - dp.parse(issue.fields.created, ignoretz=True)).days
    def hours_res(self, issue):
        """Returns number of hours since issue resolution"""
        return (dp.parse(issue.fields.customfield_10504) - dp.parse(issue.fields.created, ignoretz=True)).total_seconds()/(60*60)

    # Methods for filtering issues
    def filter_between(self, i, offset, period=PERIOD):
        """Filter issues where creation time between two days"""
        return (self.days_old(i) > offset and self.days_old(i) < period+offset)
    
    # Methods for extracting types of issues
    def get_comp(self):
        """Returns issues matching where component = self.co"""
        return [ i for i in self.issues if i.fields.components[0].name in self.co ]
    def get_open(self):
        """Returns currently open issues"""
        return [ i for i in self.get_comp() if not i.fields.customfield_10504 ]
    def get_resolved(self):
        """Returns currently resolved issues"""
        return [ i for i in self.get_comp() if i.fields.customfield_10504 ]
    def get_prev_resolved(self, offset):
        """Returns issue resolved in a PERIOD offset days ago"""
        return [ i for i in self.get_comp() if i.fields.customfield_10504 and self.filter_between(i, offset)]
    def get_new(self):
        """Returns recently created issues"""
        return [ i for i in self.get_comp() if self.filter_between(i, 0)]

    # Methods for calculating stats from lists of issues
    def percentile(self, list):
        """Calculate percentile of resolution times from a list of resolved issues"""
        if len(list):
            return np.percentile([ round(self.hours_res(i), 1) for i in list ], PERCENTILE)
        return '-'

    # Methods for outputting results
    def format_line_html(self):
        """Return one component row in HTML"""
        # Dimensions of results and alert _must_ match and defines the columns of the table generated
        results = [self.co, # Name
                   len(self.get_open()), # Open 
                   len(self.get_prev_resolved(0)), # Resolved 
                   self.percentile(self.get_prev_resolved(0)), # Current Percentile 
                   self.percentile(self.get_resolved()), # Historic Percentile
                   len(self.get_new()), # Recent issues
                   len(self.get_comp()) # All issues
                   ]
        # Sets colour of table bg. (None for black. True for red. False for green)
        alert = [None,
                 results[1] > THRESHOLD_OPEN,
                 results[2] < len(self.get_prev_resolved(PERIOD)) and results[2] > results[4],
                 (results[3] > results[4] or results[3] > THRESHOLD_AGE) and results[3] != '-',
                 results[4] > THRESHOLD_AGE and results[4] != '-',
                 results[5] > THRESHOLD_NEW,
                 False
                 ]
        lines = zip(results, alert)
        output = [ self.table_cell(x, y) for (x,y) in lines ]
        output.append('</tr>')
        return '<tr>' + ' '.join(output)

    def table_cell(self, value, alert):
        ret = "<td align='center'"
        if alert == False:
            ret += " style='background-color:%s'> %s" % ('Green', value)
        elif alert == True:
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
