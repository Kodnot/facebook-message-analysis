# bokeh basics
import pandas as pd
import numpy as np
import datetime
from math import pi

from datetime import date
from collections import defaultdict
from bokeh.layouts import column, row
from bokeh.plotting import figure
from bokeh.models import ColumnDataSource, HoverTool, Select, Panel, DateRangeSlider, Paragraph, Title
from bokeh.transform import cumsum

from bokeh.palettes import Category10_7, Turbo256

from scripts.plot_style import style
from scripts.analyser import ConvoStats


def daily_stats_tab(convoStats):

    # Daily by-party and total message counts
    def make_timeseries_dataset(convoTitle, startDate=None, endDate=None):
        convo: analyser.ConvoStats = next(
            (x for x in convoStats if x.title == convoTitle))
        participants = list(convo.countsBySender.keys())
        participantToId = {x: i for i, x in enumerate(participants)}
        totalsId = len(participants)

        xs = [[] for _ in participants] + [[]]
        ys = [[] for _ in participants] + [[]]
        color = Category10_7 if len(participants) <= 7 else Turbo256
        colors = [color[i] for i in range(len(participants)+1)]
        labels = participants + ['total']

        for date in convo.dailyCountsBySender.keys():
            convertedDate = pd.to_datetime(date)
            if startDate is not None and endDate is not None and (convertedDate < startDate or convertedDate > endDate):
                continue

            for i, (sender, count) in enumerate(convo.dailyCountsBySender[date].items()):
                participantId = participantToId[sender]

                xs[participantId].append(convertedDate)
                ys[participantId].append(count)

            xs[totalsId].append(convertedDate)
            ys[totalsId].append(sum(convo.dailyCountsBySender[date].values()))

        return ColumnDataSource(data={'x': xs, 'y': ys, 'color': colors, 'label': labels})

    def make_piechart_dataset(convoTitle, startDate=None, endDate=None):
        convo: analyser.ConvoStats = next(
            (x for x in convoStats if x.title == convoTitle))

        df = pd.DataFrame(columns=[
                          'sender', 'messageCount', 'messageCountAngle', 'f_messageCount',
                          'wordCount', 'wordCountAngle', 'f_wordCount',
                          'initiationCount', 'initiationCountAngle', 'f_initiationCount', 'color'])
        color = Category10_7 if len(convo.countsBySender) <= 7 else Turbo256

        allMessages = convo.messages
        if startDate is not None and endDate is not None:
            allMessages = list(filter(lambda m: m.datetime.date() >=
                                      startDate and m.datetime.date() <= endDate, allMessages))
        totalWordCount = sum(len(x.content.split()) for x in allMessages)
        participantCount = len(list(convo.countsBySender.keys()))

        initiationsBySender = defaultdict(int)
        for i, message in enumerate(allMessages):
            if i == 0:
                # first message, so conversation initiated
                initiationsBySender[message.sender] += 1
            else:
                timeDiff = message.datetime - allMessages[i-1].datetime
                # It is assumed that if 4h passed since last message, a new conversation has been initiated
                hoursPassed = timeDiff.total_seconds() // (60*60)
                if hoursPassed >= 4:
                    initiationsBySender[message.sender] += 1
        totalInitiationCount = sum(initiationsBySender.values())

        for i, participant in enumerate(convo.countsBySender.keys()):
            messages = list(filter(lambda m: m.sender ==
                                   participant, allMessages))

            tdf = pd.DataFrame()
            tdf['sender'] = [participant]
            tdf['messageCount'] = [len(messages)]
            # The +1/+2 is to avoid division by zero if no messages are present in the interval
            # TODO: Investigate whether I need to care about div by 0 here and in other places
            tdf['messageCountAngle'] = [
                (len(messages) + 1)/(len(allMessages) + participantCount) * 2*pi]
            tdf['f_messageCount'] = [
                f'{len(messages)} messages ({len(messages)/len(allMessages)*100:.2f}%)']
            tdf['wordCount'] = [sum(len(x.content.split()) for x in messages)]
            tdf['wordCountAngle'] = [
                (tdf['wordCount'][0] + 1) / (totalWordCount + participantCount) * 2*pi]
            tdf['f_wordCount'] = [
                f'{tdf["wordCount"][0]} words ({tdf["wordCount"][0]/totalWordCount*100:.2f}%)']
            tdf['initiationCount'] = [initiationsBySender[participant]]
            tdf['initiationCountAngle'] = [
                initiationsBySender[participant] / totalInitiationCount * 2*pi]
            tdf['f_initiationCount'] = f'{tdf["initiationCount"][0]} initations ({tdf["initiationCount"][0]/totalInitiationCount*100:.2f}%)'
            tdf['color'] = color[i]
            df = df.append(tdf)

        return ColumnDataSource(df)

    def make_messages_paragraphs(convoTitle, startDate=None, endDate=None):
        convo: analyser.ConvoStats = next(
            (x for x in convoStats if x.title == convoTitle))

        allMessages = convo.messages
        if startDate is not None and endDate is not None:
            allMessages = list(filter(lambda m: m.datetime.date() >=
                                      startDate and m.datetime.date() <= endDate, allMessages))

        rez = []
        for i, message in enumerate(allMessages):
            # TODO: The browser will crawl to a stop if I have too many messages
            # 500 messages take good 10 seconds to load
            if i > 100:
                break
            rez.append(
                f'{message.sender} ({message.datetime.strftime("%Y/%m/%d %H:%M")}): {message.content}')

        return [Paragraph(text=x, width=290) for x in rez]

    def make_timeseries_plot(src):
        p = figure(plot_width=600, plot_height=600, title='Daily message counts by date',
                   x_axis_type='datetime', x_axis_label='Date', y_axis_label='Message count')

        p.multi_line(xs='x', ys='y', source=src, color='color',
                     line_width=3, legend_field='label', line_alpha=0.4)

        # TODO: Don't know how to get the value of the multiline line, workaround with scatterplot on top?
        # TODO: That would also work better with the dates, because now I have misleading tooltips
        hover = HoverTool(tooltips=[('Count from', '@label'),
                                    ('Date', '$x{%F}'),
                                    ('Message count:', '???')],
                          formatters={'$x': 'datetime'},
                          mode='vline')  # vline means that tooltip will be shown when mouse is in a vertical line above glyph
        p.add_tools(hover)

        return p

    def _make_piechart(src, startAngle, endAngle, title, bottomTitle, tooltips):
        p = figure(plot_height=200, plot_width=280,
                   toolbar_location=None, title=title)

        p.wedge(x=0, y=1, radius=0.5, start_angle=startAngle,
                end_angle=endAngle, line_color='white', fill_color='color', source=src)
        p.axis.axis_label = None
        p.axis.visible = False
        p.grid.grid_line_color = None

        hover = HoverTool(tooltips=tooltips)
        p.add_tools(hover)

        p.add_layout(Title(text=bottomTitle, align="center"), "below")

        return p

    def make_piechart_plots(src):
        totalMessages = sum(src.data["messageCount"])
        p1 = _make_piechart(src, cumsum('messageCountAngle', include_zero=True), cumsum('messageCountAngle'),
                            'Messages sent by participant', f'Total messages: {totalMessages}',
                            [('Participant', '@sender'), ('Message count', '@f_messageCount')])

        totalWords = sum(src.data["wordCount"])
        p2 = _make_piechart(src, cumsum('wordCountAngle', include_zero=True), cumsum('wordCountAngle'),
                            'Word counts by participant', f'Total words: {totalWords}',
                            [('Participant', '@sender'), ('Word count', '@f_wordCount')])

        totalInitiations = sum(src.data["initiationCount"])
        p3 = _make_piechart(src, cumsum('initiationCountAngle', include_zero=True), cumsum('initiationCountAngle'),
                            'Conversations initiated by participant', f'Total conversations: {totalInitiations}',
                            [('Participant', '@sender'), ('Conversations initiated', '@f_initiationCount')])

        return column(p1, p2, p3)

    def _update_pie_bottom_labels():
        # Update the bottom titles of the piecharts
        for i, pie in enumerate(piePlots.children):
            # This is a bit hack-ish, but don't know a better way to do it
            if i == 0:
                totalMessages = sum(pieSrc.data["messageCount"])
                pie.below[1].text = f'Total messages: {totalMessages}'
            elif i == 1:
                totalWords = sum(pieSrc.data["wordCount"])
                pie.below[1].text = f'Total words: {totalWords}'
            elif i == 2:
                totalInitiations = sum(pieSrc.data["initiationCount"])
                pie.below[1].text = f'Total conversations: {totalInitiations}'

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

        # TODO: There is some black magic going on here, find if there is a proper way to do this
        newScr = make_timeseries_dataset(newValue)
        src.data.update(newScr.data)
        newPieSrc = make_piechart_dataset(newValue)
        pieSrc.data.update(newPieSrc.data)

        _update_pie_bottom_labels()

        messageColumn.children = make_messages_paragraphs(newValue)

    def on_date_range_changed(attr, old, new):
        convoToPlot = convoSelection.value
        startDate, endDate = dateSlider.value_as_date

        # TODO: There is some black magic going on here, find if there is a proper way to do this
        new_src = make_timeseries_dataset(convoToPlot, startDate, endDate)
        src.data.update(new_src.data)
        newPieSrc = make_piechart_dataset(convoToPlot, startDate, endDate)
        pieSrc.data.update(newPieSrc.data)

        _update_pie_bottom_labels()

        messageColumn.children = make_messages_paragraphs(
            convoToPlot, startDate, endDate)

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
    dateSlider.on_change('value_throttled', on_date_range_changed)

    src = make_timeseries_dataset(conversationTitles[0], start, end)
    p = make_timeseries_plot(src)
    p = style(p)

    pieSrc = make_piechart_dataset(conversationTitles[0], start, end)
    piePlots = make_piechart_plots(pieSrc)

    messageContents = make_messages_paragraphs(
        conversationTitles[0], start, end)

    messageColumn = column(children=messageContents,
                           height=670, width=310, css_classes=['scrollable'])
    # Wrap all controls with a single element
    controls = column(convoSelection, dateSlider)
    layout = row(controls, p, piePlots, messageColumn)
    tab = Panel(child=layout, title='Daily statistics')

    return tab
