#!/usr/bin/env python
from jira.config import get_jira
import dateutil.parser as dp
import numpy as np
import pickle

PERCENTILE = 50
THRESHOLD = 250

class gw_jira:
    def __init__(self):
        # Use config.ini, section = jira to provide server details
        # must contain user, pass, and server settings
        self.jira = get_jira(profile='jira')
        self.components = [co.name for co in self.jira.project_components(self.jira.project('PROB'))]
        self.results = []

    def get_stats(self, co):
        jql = "project=PROB and component = '%s'" % (co)
        issues = self.jira.search_issues(jql, maxResults=9999)
    	# Calculate resolution times in hours (issue.fields.customfield_10504 is the resolved date)
        times = [ (dp.parse(issue.fields.customfield_10504) - dp.parse(issue.fields.created, ignoretz=True)).total_seconds()/(60*60) for issue in issues if issue.fields.customfield_10504]
    	# Avoid errors for types with no matching issues
        if len(times):
            # Use numpy to calculate various percentiles for us
            percentile =  np.percentile(times, PERCENTILE)
            # tuple like (component, # open issues, # resolved issues, 50th, 60th, 70th, 80th)
            self.results.append( (co, len(issues)-len(times), len(times), percentile) )
            return self.results[-1]
        else:
            return False

    def format_line(self, results):
        if results:
            line = "\tOpen:\t\t\t%d\n \tClosed:\t\t\t%d\n \t%dth Percentile:\t%.2f hrs" % (results[1], results[2], PERCENTILE, results[3]) 
            # Try to read the statefile, if we fail for _any_ reason assume nothing
            try:
                prev_results = [x for x in pickle.load( open( "state.save", "rb" )) if x[0] in results[0]]
            except:
                return line
            # If percentile has risen since last run, or above THRESHOLD
            if (results[3] < prev_results[0][3]) or results[3] > THRESHOLD:
                return '\033[91m' + line + '\033[0m'
            else:
                return '\033[94m' + line + '\033[0m'
        else:
            return "No results"
            

jira = gw_jira()
for co in jira.components:
    print "%s: \n %s" % (co, jira.format_line(jira.get_stats(co)))
# Save a statefile for colouring in future runs
pickle.dump(jira.results, open( "state.save", "wb" ))
