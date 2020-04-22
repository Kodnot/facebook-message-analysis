# bokeh basics
import pandas as pd
import numpy as np
import analyser

from bokeh.layouts import column, row, WidgetBox
from bokeh.plotting import figure
from bokeh.models import ColumnDataSource, HoverTool, Select, Panel
from bokeh.models.widgets import Tabs

from bokeh.palettes import Category20_16
from bokeh.io import show, output_notebook


# TODO: This is data to use for messing around; later move all the plotting logic to a separate file, analyser.py should only have data processing
allConvoStats = analyser.analyseAll("C:\\TMP\\fbMessages")


# def make_dataset(convoTitle, startDate, endDate):
def make_dataset(convoTitle):
    convo: analyser.ConvoStats = next(
        (x for x in allConvoStats if x.title == convoTitle))
    participants = list(convo.countsBySender.keys())
    participantToId = {x: i for i, x in enumerate(participants)}

    xs = [[] for _ in participants]
    ys = [[] for _ in participants]
    colors = [Category20_16[i] for i in range(len(participants))]
    labels = participants

    for date in convo.dailyCountsBySender.keys():
        convertedDate = pd.to_datetime(date)
        for i, (sender, count) in enumerate(convo.dailyCountsBySender[date].items()):
            participantId = participantToId[sender]

            xs[participantId].append(convertedDate)
            ys[participantId].append(count)

            # tdf['f_date'] = str(convertedDate.date())

    return ColumnDataSource(data={'x': xs, 'y': ys, 'color': colors, 'label': labels})


def style(p):
    # Title
    p.title.align = 'center'
    p.title.text_font_size = '20pt'
    p.title.text_font = 'serif'

    # Axis titles
    p.xaxis.axis_label_text_font_size = '14pt'
    p.xaxis.axis_label_text_font_style = 'bold'
    p.yaxis.axis_label_text_font_size = '14pt'
    p.yaxis.axis_label_text_font_style = 'bold'

    # Tick labels
    p.xaxis.major_label_text_font_size = '12pt'
    p.yaxis.major_label_text_font_size = '12pt'

    return p


def make_plot(src):
    p = figure(plot_width=700, plot_height=700, title='Daily message counts by date',
               x_axis_type='datetime', x_axis_label='Date', y_axis_label='Message count')

    p.multi_line(xs='x', ys='y', source=src, color='color',
                 line_width=2, legend='label')

    # TODO: Don't know how to get the value of the multiline line, workaround with scatterplot on top?
    hover = HoverTool(tooltips=[('Sender', '@label'),
                                ('Date', '$x{%F}'),
                                ('Message count:', '???')],
                      formatters={'$x': 'datetime'},
                      mode='vline')  # vline means that tooltip will be shown when mouse is in a vertical line above glyph
    p.add_tools(hover)

    p = style(p)

    return p

def update(attr, old, new):
    convoToPlot = convoSelection.value
    new_src = make_dataset(convoToPlot)
    
    # TODO: There is some black magic going on here, find if there is a proper way to do this
    src.data.update(new_src.data)


src = make_dataset(allConvoStats[0].title)
p = make_plot(src)

conversationTitles = [x.title for x in allConvoStats]
convoSelection = Select(title='Conversation to analyse: ', options=conversationTitles, value=conversationTitles[0])
convoSelection.on_change('value', update)

# TODO: Add a selector for date range

# Wrap all controls with a single element
controls = WidgetBox(convoSelection)
layout = row(controls, p)
tab = Panel(child=layout, title = 'Daily statistics')
tabs = Tabs(tabs=[tab])

# Show the plot
show(tabs)
