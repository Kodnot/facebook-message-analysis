import numpy as np
import datetime
from math import pi

from bokeh.layouts import column, row
from bokeh.plotting import figure
from bokeh.models import ColumnDataSource, HoverTool, Select, Panel
from bokeh.palettes import Category10_7, Category20_20, Turbo256

from scripts.plot_style import style


def categorical_stats_tab(convoStats, convoSelection):
    conversationTitles = sorted([x.title for x in convoStats])

    def make_monthly_dataset(convoTitle):
        convo = next((x for x in convoStats if x.title == convoTitle))

        xdata_monthly = sorted(list(convo.monthlyCountsBySender.keys()))
        ydata_monthly = {participant: [convo.monthlyCountsBySender[month][participant] for month in xdata_monthly] for participant in convo.participants}

        color = Category10_7 if len(convo.participants) < 7 else Category20_20 if len(convo.participants) < 20 else Turbo256
        colors = [color[i] for i in range(len(convo.participants))]
        
        # I need separate datasets here because column lenghts differ
        return {'x_value': xdata_monthly, **ydata_monthly}, {'participants': list(convo.participants), 'colors': colors}

    def make_day_name_dataset(convoTitle):
        convo = next((x for x in convoStats if x.title == convoTitle))
        num_days = max(
            (convo.messages[-1].datetime - convo.messages[0].datetime).days, 1)
        xdataDayName = ['Monday', 'Tuesday', 'Wednesday',
                        'Thursday', 'Friday', 'Saturday', 'Sunday']
        ydataDayName = [float(convo.dayNameCounts[x]) /
                        num_days * 7 for x in xdataDayName]

        return ColumnDataSource(data={'top': ydataDayName, 'x_value': xdataDayName})

    def make_hourly_dataset(convoTitle):
        convo = next((x for x in convoStats if x.title == convoTitle))
        num_days = max(
            (convo.messages[-1].datetime - convo.messages[0].datetime).days, 1)

        xdataHourly = ['{0}:00'.format(i) for i in range(24)]
        ydataHourly = [float(convo.hourlyCounts[x]) /
                       num_days for x in range(24)]

        return ColumnDataSource(data={'top': ydataHourly, 'x_value': xdataHourly})

    def _make_histogram(src, title, xLabel, yLabel, tooltips, rotation=pi/4):
        p = figure(plot_width=550, plot_height=550, title=title, toolbar_location=None,
                   x_range=src.data['x_value'], x_axis_label=xLabel, y_axis_label=yLabel)

        p.vbar(x='x_value', top='top', width=0.9, source=src,
               fill_alpha=0.7, hover_fill_color='green', hover_fill_alpha=1.0)

        p.xaxis.major_label_orientation = rotation
        p.grid.grid_line_alpha = 0
        p.outline_line_alpha = 0

        hover = HoverTool(tooltips=tooltips)
        p.add_tools(hover)

        return p

    def make_monthly_plot(src, stackedSrc):
        p = figure(x_range=src['x_value'], plot_height=550, plot_width=550, toolbar_location=None,
                   title='Monthly message counts', x_axis_label='Date', y_axis_label='Message count', tools='hover', tooltips='@x_value: $name sent @$name messages')

        p.vbar_stack(stackedSrc['participants'], x='x_value', width=0.9, color=stackedSrc['colors'], source=src,
                    fill_alpha=0.7, legend_label=stackedSrc['participants'], hover_fill_alpha=1.0)

        p.y_range.start = 0
        p.xaxis.major_label_orientation = pi/2
        p.grid.grid_line_alpha = 0
        p.outline_line_alpha = 0
        p.legend.location = "top_left"
        p.legend.visible = True if len(stackedSrc['participants']) < 5 else False        
        p.legend.orientation = "horizontal"

        return p

    def make_day_name_plot(src):
        return _make_histogram(src, 'Average messsages per weekday', 'Weekday', 'Average message count',
                               [('Average message count', '@top'), ('Weekday', '@x_value')])

    def make_hourly_plot(src):
        return _make_histogram(src, 'Average messages per hour of the day', 'Hour', 'Average message count',
                               [('Average message count', '@top'), ('Hour', '@x_value')])

    def on_conversation_changed(attr, oldValue, newValue):
        newMonthlySrc, newMonthlyStackedSrc = make_monthly_dataset(newValue)
        newDayNameSrc = make_day_name_dataset(newValue)
        newHourlySrc = make_hourly_dataset(newValue)
        # I have to redraw the whole plot, since I need to pass the x range to figure for categorical data
        plotRow.children = [make_monthly_plot(newMonthlySrc, newMonthlyStackedSrc),
                            make_day_name_plot(newDayNameSrc),
                            make_hourly_plot(newHourlySrc)]

    convoSelection.on_change('value', on_conversation_changed)

    monthlySrc, monthlyStackedSrc = make_monthly_dataset(conversationTitles[0])
    monthlyPlot = make_monthly_plot(monthlySrc, monthlyStackedSrc)

    dayNameSrc = make_day_name_dataset(conversationTitles[0])
    dayNamePlot = make_day_name_plot(dayNameSrc)

    hourlySrc = make_hourly_dataset(conversationTitles[0])
    hourlyPlot = make_hourly_plot(hourlySrc)

    plotRow = row(monthlyPlot, dayNamePlot, hourlyPlot)
    layout = column(row(convoSelection), plotRow)
    tab = Panel(child=layout, title='Categorical statistics')

    return tab
