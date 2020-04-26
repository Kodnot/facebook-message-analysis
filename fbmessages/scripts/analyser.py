from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
from collections import namedtuple, defaultdict
from operator import itemgetter
from nltk.corpus import stopwords
from unidecode import unidecode

from bokeh.plotting import figure
from bokeh.io import show

import numpy as np
import matplotlib.pyplot as plt
import datetime
import heapq
import string
import time
import json
import copy
import os
import glob


class Message:
    def __init__(self, sender, datetime, content):
        self.sender = sender
        self.datetime = datetime
        self.content = content
        
    def __str__(self):
        return f'{self.sender}: {self.content}'

class ConvoStats:
    def __init__(self, title):
        self.title = title
        self.participants = set()
        self.messages = []
        self.dailyCountsBySender = {}
        
        self.totalMessages = 0
        self.initiationsBySender = defaultdict(int)
        self.countsBySender = defaultdict(int)

    def __str__(self):
        rez = f'Convo: {self.title}, total messages: {self.totalMessages}\n'
        for key, val in sorted(self.countsBySender.items(), key=lambda p: p[1], reverse=True):
            rez += f'{key} sent {val} messages, {val/self.totalMessages*100}% of total messages\n'

        totalStartedConvos = sum(self.initiationsBySender.values())
        for key, val in sorted(self.initiationsBySender.items(), key=lambda p: p[1], reverse=True):
            rez += f'{key} initiated {val} conversations, {val/totalStartedConvos*100}% of total\n'
        return rez


english_stopwords = set(stopwords.words('english'))
sentiment_analyzer = SentimentIntensityAnalyzer()

# The unicode in the json files is misformatted: https://stackoverflow.com/questions/50004087/converting-unicode-string-to-utf-8
def parse_utf8(s):
    arr = bytearray(map(ord, s))
    return arr.decode('utf-8')

# loads messages from files in filenames (message files may be split into multiple files)
def _load_messages(filenames):
    data = None
    for filename in filenames:
        with open(filename) as jsonfile:
            tData = json.load(jsonfile)
            if data is None:
                data = tData
            else:
                data['messages'] += tData['messages']
                
    # parse unicode
    data['title'] = parse_utf8(data['title'])
    
    for msg in data['messages']:
        msg['sender_name'] = parse_utf8(msg['sender_name'])
        if 'content' in msg:
            msg['content'] = parse_utf8(msg['content'])
    return data


def get_messages(data):
    # Copy the stored messages we have
    copied_messages = data['messages']

    # Return a sorted list of messages by time
    return sorted(copied_messages, key=lambda message: message['timestamp_ms'])


def analyze(filenames):
    # Load messages
    print(f'Reading files {filenames} ...')
    timestamp = time.perf_counter()
    data = _load_messages(filenames)
    messages = get_messages(data)
    print('Loaded {0} messages in {1:.2f} seconds.'.format(
        len(messages), time.perf_counter() - timestamp))

    # To avoid issues, convos with <10 messages will be ignored
    if len(messages) < 10:
        # TODO: Commented this out due to some bogus encoding error, investigate later
        # TODO: (Might go away if I fix my data encodings right after reading it, it's a mess rn)
        # print(f'Conversation {data["title"]} is ignored due to small size')
        return None

    print('Aggregating data ...')
    timestamp = time.perf_counter()

    # Data structures to hold information about the messages
    processedMessages = []
    countsBySender = defaultdict(int)
    initiationsBySender = defaultdict(int)
    daily_counts = defaultdict(int)

    dailyCountsBySender = {}

    daily_sticker_counts = defaultdict(int)
    daily_sentiments = defaultdict(float)
    monthly_counts = defaultdict(int)
    monthly_sticker_counts = defaultdict(int)
    hourly_counts = defaultdict(int)
    day_name_counts = defaultdict(int)
    word_frequencies = defaultdict(int)
    first_date = None
    last_date = None
    participants = set()

    # Extract information from the messages
    for id, message in enumerate(messages):
        participants.add(message['sender_name'])
        # Convert message's Unix timestamp to local datetime
        date = datetime.datetime.fromtimestamp(message['timestamp_ms']/1000.0)
        month = date.strftime('%Y-%m')
        day = date.strftime('%Y-%m-%d')
        day_name = date.strftime('%A')
        hour = date.time().hour

        # track who initiated the conversations how many times
        if id == 0:
            # first message, so conversation initiated
            initiationsBySender[message['sender_name']] += 1
        else:
            timeDiff = date - \
                datetime.datetime.fromtimestamp(
                    messages[id-1]['timestamp_ms']/1000.0)
            # It is assumed that if 4h passed since last message, a new conversation has been initiated
            hoursPassed = timeDiff.total_seconds() // (60*60)
            if hoursPassed >= 4:
                initiationsBySender[message['sender_name']] += 1

        # Increment message counts
        countsBySender[message['sender_name']] += 1
        hourly_counts[hour] += 1
        day_name_counts[day_name] += 1
        daily_counts[day] += 1

        if day not in dailyCountsBySender:
            dailyCountsBySender[day] = defaultdict(int)
        dailyCountsBySender[day][message['sender_name']] += 1

        monthly_counts[month] += 1
        if 'sticker' in message:
            daily_sticker_counts[day] += 1
            monthly_sticker_counts[month] += 1

        # Process content of the message if it has any
        if 'content' in message:
            content = message['content']
            processedMessages.append(Message(message['sender_name'], date, content))
            # Rudimentary sentiment analysis using VADER
            sentiments = sentiment_analyzer.polarity_scores(content)
            daily_sentiments[day] += sentiments['pos'] - sentiments['neg']

            # Split message up by spaces to get individual words
            for word in content.split(' '):
                # Make the word lowercase and strip it of punctuation
                new_word = word.lower().strip(string.punctuation)

                # Word might have been entirely punctuation; don't strip it
                if not new_word:
                    new_word = word.lower()

                # Ignore word if it in the stopword set or if it is less than 2 characters
                if len(new_word) > 1 and new_word not in english_stopwords:
                    word_frequencies[new_word] += 1

        # Determine start and last dates of messages
        if (first_date and first_date > date) or not first_date:
            first_date = date
        if (last_date and last_date < date) or not last_date:
            last_date = date

    # Take the average of the sentiment amassed for each day
    for day, message_count in daily_counts.items():
        daily_sentiments[day] /= message_count

    # Get the number of days the messages span over
    num_days = max((last_date - first_date).days, 1)

    # Get most common words
    top_words = heapq.nlargest(42, word_frequencies.items(), key=itemgetter(1))

    print('Processed data in {0:.2f} seconds.'.format(
        time.perf_counter() - timestamp))

    rezStats = ConvoStats(data['title'])
    rezStats.countsBySender = countsBySender
    rezStats.initiationsBySender = initiationsBySender
    rezStats.totalMessages = len(messages)
    rezStats.dailyCountsBySender = dailyCountsBySender
    rezStats.messages = processedMessages
    rezStats.participants = participants

    print('Preparing data for display ...')

    # Format data for graphing
    xdata_daily = sorted(list(daily_counts.keys()))
    ydata_daily = [daily_counts[x] for x in xdata_daily]
    ydata_daily_stickers = [daily_sticker_counts[x] for x in xdata_daily]
    xdata_monthly = sorted(list(monthly_counts.keys()))
    ydata_monthly = [monthly_counts[x] for x in xdata_monthly]
    ydata_monthly_stickers = [monthly_sticker_counts[x] for x in xdata_monthly]
    xdata_day_name = ['Sunday', 'Monday', 'Tuesday',
                      'Wednesday', 'Thursday', 'Friday', 'Saturday']
    ydata_day_name = [float(day_name_counts[x]) /
                      num_days * 7 for x in xdata_day_name]
    xdata_hourly = ['{0}:00'.format(i) for i in range(24)]
    ydata_hourly = [float(hourly_counts[x]) / num_days for x in range(24)]
    xdata_sentiment = sorted(list(daily_sentiments.keys()))
    ydata_sentiment = [daily_sentiments[x] for x in xdata_sentiment]
    xdata_top_words, ydata_top_words = zip(*top_words)

    print('Displaying ...')

    # Generate subplots
    # fig, ax_array = plt.subplots(2, 3)

    def show_daily_total_graph(ax, xdata, ydata, ydata_stickers):
        indices = np.arange(len(xdata))

        ax.plot(indices, ydata,
                alpha=1.0, color='dodgerblue',
                label='All messages')

        ax.plot(indices, ydata_stickers,
                alpha=1.0, color='orange',
                label='Facebook stickers')

        ax.set_xlabel('Date')
        ax.set_ylabel('Count')
        ax.set_title('Number of messages exchanged every day')

        num_ticks = 16 if len(indices) >= 16 else len(indices)
        tick_spacing = round(len(indices) / num_ticks)
        ticks = [tick_spacing *
                 i for i in range(num_ticks) if tick_spacing * i < len(xdata)]
        tick_labels = [xdata[tick] for tick in ticks]

        ax.set_xticks(ticks)
        ax.set_xticklabels(tick_labels)
        for tick in ax.get_xticklabels():
            tick.set_rotation(30)

        ax.legend()

    def show_monthly_total_graph(ax, xdata, ydata, ydata_stickers):
        indices = np.arange(len(xdata))

        ax.bar(indices, ydata,
               alpha=1.0, color='dodgerblue',
               label='All messages')

        ax.bar(indices, ydata_stickers,
               alpha=1.0, color='orange',
               label='Facebook stickers')

        ax.set_xlabel('Date')
        ax.set_ylabel('Count')
        ax.set_title('Number of messages exchanged every month')

        ax.set_xticks(indices)
        ax.set_xticklabels(xdata)
        for tick in ax.get_xticklabels():
            tick.set_rotation(30)

        ax.legend()

    def show_day_name_average_graph(ax, xdata, ydata):
        indices = np.arange(len(xdata))
        bar_width = 0.6

        ax.bar(indices, ydata, bar_width,
               alpha=1.0, color='dodgerblue',
               align='center',
               label='All messages')

        ax.set_xlabel('Day of the Week')
        ax.set_ylabel('Count')
        ax.set_title('Average number of messages every day of the week')

        ax.set_xticks(indices)
        ax.set_xticklabels(xdata)

    def show_hourly_average_graph(ax, xdata, ydata):
        indices = np.arange(len(xdata))
        bar_width = 0.8

        ax.bar(indices, ydata, bar_width,
               alpha=1.0, color='dodgerblue',
               align='center',
               label='All messages')

        ax.set_xlabel('Hour')
        ax.set_ylabel('Count')
        ax.set_title('Average number of messages every hour of the day')

        ax.set_xticks(indices)
        ax.set_xticklabels(xdata)
        for tick in ax.get_xticklabels():
            tick.set_rotation(30)

    def show_daily_sentiment_graph(ax, xdata, ydata):
        indices = np.arange(len(xdata))

        ax.plot(indices, ydata,
                alpha=1.0, color='darkseagreen',
                label='VADER sentiment')

        ax.set_xlabel('Date')
        ax.set_ylabel('Sentiment')
        ax.set_title('Average sentiment over time')

        num_ticks = 16 if len(indices) >= 16 else len(indices)
        tick_spacing = round(len(indices) / num_ticks)
        ticks = [tick_spacing *
                 i for i in range(num_ticks) if tick_spacing * i < len(xdata)]
        tick_labels = [xdata[tick] for tick in ticks]

        ax.set_xticks(ticks)
        ax.set_xticklabels(tick_labels)
        for tick in ax.get_xticklabels():
            tick.set_rotation(30)
        ax.set_ylim([-1.0, 1.0])

        ax.legend()

    def show_top_words_graph(ax, xdata, ydata):
        indices = np.arange(len(xdata))
        bar_width = 0.8

        ax.barh(indices, ydata, bar_width,
                alpha=1.0, color='orchid',
                align='center',
                label='All messages')

        ax.set_ylabel('Word')
        ax.set_xlabel('Uses')
        ax.set_title('Our {0} most used words'.format(len(xdata)))

        ax.set_yticks(indices)
        ax.set_yticklabels(xdata)

    # Call the graphing methods
    # show_daily_total_graph(ax_array[0][0], xdata_daily, ydata_daily, ydata_daily_stickers)
    # show_monthly_total_graph(ax_array[0][1], xdata_monthly, ydata_monthly, ydata_monthly_stickers)
    # show_daily_sentiment_graph(ax_array[0][2], xdata_sentiment, ydata_sentiment)
    # show_day_name_average_graph(ax_array[1][0], xdata_day_name, ydata_day_name)
    # show_hourly_average_graph(ax_array[1][1], xdata_hourly, ydata_hourly)
    # show_top_words_graph(ax_array[1][2], xdata_top_words[::-1], ydata_top_words[::-1])

    # Display the plots
    # plt.show()

    print('Done.')

    return rezStats


def analyseAll(folderName):
    rez = []
    for dirName, subdirList, fileList in os.walk(folderName):
        messageFiles = glob.glob(os.path.join(dirName, 'message*'))
        if len(messageFiles) > 0:
            convoStats = analyze(messageFiles)
            if convoStats is not None:
                rez.append(convoStats)
    return sorted(rez, key=lambda dt: dt.totalMessages, reverse=True)
