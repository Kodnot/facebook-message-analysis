import argparse
import analyser

parser = argparse.ArgumentParser(description='Tool to analyze your Facebook Messenger history')
parser.add_argument('folder', help='The folder containing Facebook chat messages in JSON format, or a folder of such folders')

args = parser.parse_args()
allConvoStats = analyser.analyseAll(args.folder)

for convoStats in allConvoStats:
    print(str(convoStats))
    