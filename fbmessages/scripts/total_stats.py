import pandas as pd
import numpy as np

from bokeh.layouts import column, row
from bokeh.models import ColumnDataSource, Panel, CheckboxGroup
from bokeh.models.widgets import TableColumn, DataTable
from unidecode import unidecode

from scripts.analyser import ConvoStats


def total_stats_tab(convoStats):
    conversationTitles = sorted([x.title for x in convoStats])

    def make_dataset(convoTitles):

        df = pd.DataFrame(
            columns=['title', 'messagesSent', 'conversationsInitiated'])
        convoStats.sort(key=lambda x: x.title)

        for stats in convoStats:
            if stats.title not in convoTitles:
                continue

            totalMessages = stats.totalMessages
            totalInitiations = sum(stats.initiationsBySender.values())
            for participant in sorted(stats.countsBySender.keys()):
                tdf = pd.DataFrame()
                tdf['title'] = [f'{stats.title} ({participant})']
                tSent = stats.countsBySender[participant]
                tdf['messagesSent'] = [
                    f'{tSent} out of {totalMessages} ({tSent/totalMessages*100:.2f}%)']
                tInitiated = stats.initiationsBySender[participant]
                tdf['conversationsInitiated'] = [
                    f'{tInitiated} out of {totalInitiations} ({tInitiated/totalInitiations*100:.2f}%)']
                df = df.append(tdf)

        return ColumnDataSource(df)

    def make_table(src):

        # Columns of table
        table_columns = [TableColumn(field='title', title='Chat and participant'),
                         TableColumn(field='messagesSent',
                                     title='Messages sent'),
                         TableColumn(field='conversationsInitiated',
                                     title='Conversations initiated')]

        stats_table = DataTable(
            source=src, columns=table_columns, sizing_mode='stretch_both')
        return stats_table

    def on_conversation_selection_changed(attr, oldValue, newValue):
        convoTitles = [conversationTitles[i] for i in convoSelection.active]
        newSrc = make_dataset(convoTitles)
        src.data.update(newSrc.data)

    # A dropdown list to select a conversation
    convoSelection = CheckboxGroup(
        labels=conversationTitles, active=list(range(len(conversationTitles))))
    convoSelection.on_change('active', on_conversation_selection_changed)

    src = make_dataset(conversationTitles)
    stats_table = make_table(src)

    controls = column(convoSelection)
    layout = row(controls, stats_table)

    tab = Panel(child=layout, title='Total Stats Table')

    return tab
