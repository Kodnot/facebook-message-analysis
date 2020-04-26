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
        self.monthlyCounts = defaultdict(int)
        self.dayNameCounts = defaultdict(int)
        self.hourlyCounts = defaultdict(int)
        self.dailySentiments = defaultdict(float)
        self.wordFrequencies = []
        
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
            daily_sentiments[day] += sentiments['compound']

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
    rezStats.monthlyCounts = monthly_counts
    rezStats.dayNameCounts = day_name_counts
    rezStats.hourlyCounts = hourly_counts
    rezStats.dailySentiments = daily_sentiments
    rezStats.wordFrequencies = word_frequencies

    print('Preparing data for display ...')

    xdata_top_words, ydata_top_words = zip(*top_words)

    print('Displaying ...')

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
