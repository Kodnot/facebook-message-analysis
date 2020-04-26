import numpy as np
import pandas as pd
import datetime
import heapq
from math import pi
from operator import itemgetter

from bokeh.layouts import column, row
from bokeh.plotting import figure
from bokeh.models import ColumnDataSource, HoverTool, Select, Panel

from scripts.plot_style import style


def misc_stats_tab(convoStats):
    conversationTitles = sorted([x.title for x in convoStats])

    def make_sentiment_dataset(convoTitle):
        convo = next((x for x in convoStats if x.title == convoTitle))

        xdataSentiment = sorted([pd.to_datetime(x)
                                 for x in convo.dailySentiments.keys()])
        ydataSentiment = [convo.dailySentiments[x]
                          for x in convo.dailySentiments.keys()]

        return ColumnDataSource(data={'date': xdataSentiment, 'sentiment': ydataSentiment})

    def make_common_words_dataset(convoTitle, minLen=0):
        convo = next((x for x in convoStats if x.title == convoTitle))

        top_words = heapq.nlargest(20, filter(
            lambda x: len(x[0]) >= minLen, convo.wordFrequencies.items()), key=itemgetter(1))

        xdata_top_words, ydata_top_words = zip(*reversed(top_words))
        return ColumnDataSource(data={'word': xdata_top_words, 'count': ydata_top_words})

    def make_sentiment_plot(src):
        p = figure(plot_width=550, plot_height=550, title='Daily VADER sentiment', y_range=(-1, 1),
                   x_axis_type='datetime', x_axis_label='Date', y_axis_label='Sentiment value')

        p.line(x='date', y='sentiment', source=src,
               line_width=2, color='green')
        hover = HoverTool(tooltips=[('Sentiment value', '@sentiment'),
                                    ('Date', '@date{%F}')],
                          formatters={'@date': 'datetime'},
                          mode='vline')  # vline means that tooltip will be shown when mouse is in a vertical line above glyph
        p.add_tools(hover)

        return p

    def make_common_words_plot(src, minLen=0):
        p = figure(plot_width=550, plot_height=550, title=f'Most common words with len >= {minLen}',
                   toolbar_location=None, y_range=src.data['word'], x_axis_label='Number of occurrences', y_axis_label='Words')

        p.hbar(y='word', right='count', height=0.9, source=src,
               fill_alpha=0.7, hover_fill_color='green', hover_fill_alpha=1.0)

        # p.xaxis.major_label_orientation = rotation
        p.grid.grid_line_alpha = 0
        p.outline_line_alpha = 0

        hover = HoverTool(
            tooltips=[('Word', '@word'), ('No. of occurrences', '@count')])
        p.add_tools(hover)

        return p

    def on_conversation_changed(attr, oldValue, newValue):
        newSentimentSrc = make_sentiment_dataset(newValue)
        sentimentSrc.data.update(newSentimentSrc.data)

        newCommonWordsAllSrc = make_common_words_dataset(newValue)
        newCommonWordsLongSrc = make_common_words_dataset(newValue, 5)
        plotRow.children = [sentimentPlot, make_common_words_plot(newCommonWordsAllSrc),
                            make_common_words_plot(newCommonWordsLongSrc, 5)]

    convoSelection = Select(title='Conversation to analyse: ',
                            options=conversationTitles, value=conversationTitles[0])
    convoSelection.on_change('value', on_conversation_changed)

    sentimentSrc = make_sentiment_dataset(conversationTitles[0])
    sentimentPlot = make_sentiment_plot(sentimentSrc)

    commonWordsAllSrc = make_common_words_dataset(conversationTitles[0])
    commonWordsAllPlot = make_common_words_plot(commonWordsAllSrc)

    commonWordsLongSrc = make_common_words_dataset(conversationTitles[0], 5)
    commonWordsLongPlot = make_common_words_plot(commonWordsLongSrc, 5)

    plotRow = row(sentimentPlot, commonWordsAllPlot, commonWordsLongPlot)
    layout = column(row(convoSelection), plotRow)
    tab = Panel(child=layout, title='Misc statistics')

    return tab
