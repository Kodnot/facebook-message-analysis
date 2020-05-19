import argparse
import ptvsd
import os

from bokeh.io import curdoc
from bokeh.models.widgets import Tabs

from scripts.analyser import analyseAll

# tabs
from scripts.daily_stats import daily_stats_tab
from scripts.categorical_stats import categorical_stats_tab
from scripts.misc_stats import misc_stats_tab
from bokeh.models.widgets.inputs import Select

# attach to VS Code debugger if this script was run with BOKEH_VS_DEBUG=true
if 'BOKEH_VS_DEBUG' in os.environ and os.environ['BOKEH_VS_DEBUG'] == 'true':
    # 5678 is the default attach port in the VS Code debug configurations
    print('Waiting for debugger attach')
    ptvsd.enable_attach(address=('localhost', 5678), redirect_output=True)
    ptvsd.wait_for_attach()

parser = argparse.ArgumentParser(description='Tool to analyze your Facebook Messenger history')
parser.add_argument('folder', help='The folder containing Facebook chat messages in JSON format, or a folder of such folders')

args = parser.parse_args()
allConvoStats = analyseAll(args.folder)

# pass the same select object to all tabs so that they synchronise
# TODO: This approach causes errors about being unable to update object which is no longer in document, probably because the callbacks try to update items in non-active tabs.
# However, the overall behavior is still as intended, so I'll leave it like this for now.
conversationTitles = sorted([x.title for x in allConvoStats])
convoSelection = Select(title='Conversation to analyse: ',
                        options=conversationTitles, value=conversationTitles[0])

tab1 = daily_stats_tab(allConvoStats, convoSelection)
tab2 = categorical_stats_tab(allConvoStats, convoSelection)
tab3 = misc_stats_tab(allConvoStats, convoSelection)

# Put all tabs into one app
tabs = Tabs(tabs=[tab1, tab2, tab3])

# Put the tabs in the current document for display
curdoc().add_root(tabs)
