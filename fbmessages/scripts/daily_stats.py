# bokeh basics
import pandas as pd
import numpy as np

from datetime import date
from bokeh.layouts import column, row
from bokeh.plotting import figure
from bokeh.models import ColumnDataSource, HoverTool, Select, Panel, DateRangeSlider

from bokeh.palettes import Category10_7, Turbo256

from scripts.plot_style import style
from scripts.analyser import ConvoStats


def daily_stats_tab(convoStats):

    # Daily by-party and total message counts
    def make_dataset(convoTitle, startDate=None, endDate=None):
        convo: analyser.ConvoStats = next(
            (x for x in convoStats if x.title == convoTitle))
        participants = list(convo.countsBySender.keys())
        participantToId = {x: i for i, x in enumerate(participants)}

        xs = [[] for _ in participants]
        ys = [[] for _ in participants]
        color = Category10_7 if len(participants) <= 7 else Turbo256
        colors = [color[i] for i in range(len(participants))]
        labels = participants

        for date in convo.dailyCountsBySender.keys():
            convertedDate = pd.to_datetime(date)
            if startDate is not None and endDate is not None and (convertedDate < startDate or convertedDate > endDate):
                continue

            for i, (sender, count) in enumerate(convo.dailyCountsBySender[date].items()):
                participantId = participantToId[sender]

                xs[participantId].append(convertedDate)
                ys[participantId].append(count)

        return ColumnDataSource(data={'x': xs, 'y': ys, 'color': colors, 'label': labels})

    def make_plot(src):
        p = figure(plot_width=600, plot_height=600, title='Daily message counts by date',
                   x_axis_type='datetime', x_axis_label='Date', y_axis_label='Message count')

        p.multi_line(xs='x', ys='y', source=src, color='color',
                     line_width=3, legend_field='label', line_alpha=0.6)

        # TODO: Don't know how to get the value of the multiline line, workaround with scatterplot on top?
        # TODO: That would also work better with the dates, because now I have misleading tooltips
        hover = HoverTool(tooltips=[('Sender', '@label'),
                                    ('Date', '$x{%F}'),
                                    ('Message count:', '???')],
                          formatters={'$x': 'datetime'},
                          mode='vline')  # vline means that tooltip will be shown when mouse is in a vertical line above glyph
        p.add_tools(hover)

        return p

    def on_conversation_changed(attr, oldValue, newValue):
        convo: analyser.ConvoStats = next(
            (x for x in convoStats if x.title == newValue))

        # When switching to a new convo, update the date range slider to match convo data ranges
        initialDates = list(convo.dailyCountsBySender.keys())
        start = pd.to_datetime(initialDates[0]).date()
        end = pd.to_datetime(initialDates[-1]).date()
        dateSlider.start = start
        dateSlider.end = end
        dateSlider.value = (start, end)
        new_src = make_dataset(newValue)

        # TODO: There is some black magic going on here, find if there is a proper way to do this
        src.data.update(new_src.data)

    def on_date_range_changed(attr, old, new):
        convoToPlot = convoSelection.value
        startDate, endDate = dateSlider.value_as_date
        new_src = make_dataset(convoToPlot, startDate, endDate)

        # TODO: There is some black magic going on here, find if there is a proper way to do this
        src.data.update(new_src.data)

    # A dropdown list to select a conversation
    conversationTitles = sorted([x.title for x in convoStats])
    convoSelection = Select(title='Conversation to analyse: ',
                            options=conversationTitles, value=conversationTitles[0])
    convoSelection.on_change('value', on_conversation_changed)

    # A slider to select a date range for the analysis
    initialConvo: analyser.ConvoStats = next(
        (x for x in convoStats if x.title == conversationTitles[0]))
    initialDates = list(initialConvo.dailyCountsBySender.keys())
    start = pd.to_datetime(initialDates[0]).date()
    end = pd.to_datetime(initialDates[-1]).date()
    dateSlider = DateRangeSlider(
        title='Date interval:', start=start, end=date.today(), value=(start, end), step=1)
    dateSlider.on_change('value', on_date_range_changed)

    src = make_dataset(conversationTitles[0], start, end)
    p = make_plot(src)
    p = style(p)

    # Wrap all controls with a single element
    controls = column(convoSelection, dateSlider)
    layout = row(controls, p)
    tab = Panel(child=layout, title='Daily statistics')

    return tab
