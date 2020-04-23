import pandas as pd
import numpy as np

from bokeh.models import ColumnDataSource, Panel
from bokeh.models.widgets import TableColumn, DataTable
from unidecode import unidecode

from scripts.analyser import ConvoStats


def total_stats_tab(convoStats):

    df = pd.DataFrame(
        columns=['title', 'messagesSent', 'conversationsInitiated'])
    convoStats.sort(key=lambda x: x.title)

    for stats in convoStats:
        totalMessages = stats.totalMessages
        totalInitiations = sum(stats.initiationsBySender.values())
        for participant in sorted(stats.countsBySender.keys()):
            tdf = pd.DataFrame()
            tdf['title'] = [f'{stats.title} ({participant})']
            tSent = stats.countsBySender[participant]
            tdf['messagesSent'] = [f'{tSent} out of {totalMessages} ({tSent/totalMessages*100:.2f}%)']
            tInitiated = stats.initiationsBySender[participant]
            tdf['conversationsInitiated'] = [f'{tInitiated} out of {totalInitiations} ({tInitiated/totalInitiations*100:.2f}%)']
            df = df.append(tdf)

    src = ColumnDataSource(df)

    # Columns of table
    table_columns = [TableColumn(field='title', title='Chat and participant'),
                     TableColumn(field='messagesSent',
                                 title='Messages sent'),
                     TableColumn(field='conversationsInitiated',
                                 title='Conversations initiated')]

    stats_table = DataTable(
        source=src, columns=table_columns, sizing_mode='stretch_both')

    tab = Panel(child=stats_table, title='Total Stats Table')

    return tab
