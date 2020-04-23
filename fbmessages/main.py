from bokeh.io import curdoc
from bokeh.models.widgets import Tabs

from scripts.analyser import analyseAll

# tabs
from scripts.daily_stats import daily_stats_tab


allConvoStats = analyseAll("C:\\TMP\\fbMessages")

tab1 = daily_stats_tab(allConvoStats)

# Put all tabs into one app
tabs = Tabs(tabs=[tab1])

# Put the tabs in the current document for display
curdoc().add_root(tabs)
