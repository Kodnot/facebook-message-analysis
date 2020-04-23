import argparse

from bokeh.io import curdoc
from bokeh.models.widgets import Tabs

from scripts.analyser import analyseAll

# tabs
from scripts.daily_stats import daily_stats_tab

parser = argparse.ArgumentParser(description='Tool to analyze your Facebook Messenger history')
parser.add_argument('folder', help='The folder containing Facebook chat messages in JSON format, or a folder of such folders')

args = parser.parse_args()
allConvoStats = analyseAll(args.folder)

tab1 = daily_stats_tab(allConvoStats)

# Put all tabs into one app
tabs = Tabs(tabs=[tab1])

# Put the tabs in the current document for display
curdoc().add_root(tabs)
