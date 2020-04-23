# facebook-message-analysis

1. Download your Facebook messenger history from your Facebook settings. 
[More here.](https://www.zapptales.com/en/download-facebook-messenger-chat-history-how-to/)
1. Unzip your data into the directory of your choice.
1. Identify a person whose chat history you want to analyze (if you want to run analysis for a single person) and copy the path to his subdirectory, or copy the path to the root data directory.
    1. We will refer to this folder's path as **${FOLDER}**.
1. Clone this repository and change directory into it.
```
git clone https://github.com/Kodnot/facebook-message-analysis.git && cd facebook-message-analysis
```
5. Install any dependencies.
```
pip install -r requirements.txt
```
6. If you get an NTLK download error, use this command to resolve the issue. 
It will tell NTLK to download the appropriate stopwords file.
```
python
>>> import nltk
>>> nltk.download('stopwords')
>>> quit()
```
7. Launch the bokeh app locally, passing the folder containing the conversation files as an argument
```
bokeh serve --show fbmessages/ --args **${FOLDER}**
```

In a few seconds, you should get some nice interactive visualizations. Have fun!