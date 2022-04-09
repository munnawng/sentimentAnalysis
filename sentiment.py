# Munnawn, uniqname: munnawng
# EECS 486 final project

# usage: python sentiment.py
from flask import Flask
from datetime import date
from bs4 import BeautifulSoup
import requests
from transformers import DistilBertForSequenceClassification, DistilBertTokenizerFast, TextClassificationPipeline
from json import dumps, loads

app = Flask(__name__)

ticker_list = ["AAPL", "AMD", "AMZN", "BABA", "FB", "XOM", "CVX", "CLR", "EQT", "PXD", "WMT", "TGT", "GME", "COST", "LULU", "BAC", "JPM", "GS", "COF", "WFC"]
tickers = {
    "Technology": {"AAPL", "AMD", "AMZN", "BABA", "FB"},
    "Energy": {"XOM", "CVX", "CLR", "EQT", "PXD"},
    "Retail": {"WMT", "TGT", "GME", "COST", "LULU"},
    "Finance": {"BAC", "JPM", "GS", "COF", "WFC"}
}
headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/98.0.4758.102 Safari/537.36'}

# Parses through the html and extracts links in the id="news-table" 
# section for the current day (tab-link-news)
# INPUT: name of current ticker (string)
# INPUT: html of a finviz ticker page as BeautifulSoup object
# INPUT: dicitonary key=ticker name, val=list of strings (all news articles for the current day)
# INPUT: todays_date = string representing todays date in format: "Mar-26-22"
# OUTPUT: the dictionary filled
def find_ticker_info(ticker, html, ticker_articles, todays_date):
    news_table = html.find('table', attrs = {'id': 'news-table'})
    news_table_rows = news_table.find_all('tr')
    for row in news_table_rows:
        date_item = row.find('td')
        article_date = date_item.text

        # check if article_date == todays_date. 
        # article_date format is "Mar-26-22 12:32AM" at a date label and "1:22AM"
        # if it's in the same date but different time
        
        # We first check if length of string is high, to see if it is a date label rather than regular.
        # Then we check if the date is today's date
        if len(article_date) > 9:
            if article_date.split()[0] != todays_date:
                break
        
        a_tags = row.find_all('a', href=True)

        for a_tag in a_tags:
            URL = a_tag['href']
            title = a_tag.text

            # making sure that the URL isn't nothing
            if (len(URL) == 0 or URL == "/"):
                continue

            ticker_articles[ticker].append(title)
    # END FOR that goes through all of today's articles

    return ticker_articles
# END find_ticker_info()

# might delete this func since it is hard to distinguish between relevant article text and junk like "subscribe to keep reading"
# function that extracts the article title + some of the article text
# INPUT: URL string
# INPUT: title of the article string
# OUTPUT: string = article title + first paragraph of the article text (if heuristic works)
def extract_article_data(URL,title):
    article_data = title

    try:
        r = session.get(URL, headers = headers, timeout = 3)
    except:
        print('ERROR: Web site does not exist or too many redirects or timeout')
        return ""
    
    html = BeautifulSoup(r.content, features='html.parser')
    
    # The article text is written in p tags.
    # The web page has many p tags that are irrelevant to the article.
    # Like for example, suggestions for other articles--irrelevant.
    
    # Heuristic: we will save the title and only the first 
    # p tag (first paragraph in article) after the title
    # UPDATE: heuristic does not work since title is not always the same between finviz and the actual article...
    print(URL)
    print(title)
    # below displays how the title from finviz does not match the article's title (which has a newline character)
    # if I do the .find() without the newline character it returns a None object and then will error on a later line
    if title == "Dow Jones Futures: What The Market Rally Needs Now; Six Stocks In Focus, Tesla Rival Xpeng On Tap":
        print(html.find(text="\nDow Jones Futures: What The Market Rally Needs Now; Six Stocks In Focus, Tesla Rival Xpeng On Tap	").parent)
    title_area = html.find(text=title).parent
    relevant_item = title_area.findNext('p')
    relevant_text = relevant_item.text

    article_data += relevant_text

    return article_data


def calc_sentiment(pred_dicts):
    # Takes in the a list of lists of dictionaries containing scores for each label (pos, neg, neutral)
    # for each article of a given ticker and calculates a total sentiment between -1 and 1
    # This is confusing but basically the format for 1 article would look like
    # [[{'label':'LABEL_0', 'score':'0.6897'}, {etc.}]]
    sum_pos = 0
    sum_neg = 0
    n_articles = len(pred_dicts)
    best_ind, best_score = -1, 0
    worst_ind, worst_score = -1, 0

    if n_articles == 0:
        return 0, 0, -1, 0, -1, 0

    for n, article in enumerate(pred_dicts):
        for dict in article:
            if '0' in dict['label']:
                neg_score = dict['score']
                sum_neg += neg_score
            elif '2' in dict['label']:
                pos_score = dict['score']
                sum_pos += pos_score

        art_score = pos_score - neg_score
        if art_score > best_score:
            best_score = art_score
            best_ind = n
        elif art_score < worst_score:
            worst_score = art_score
            worst_ind = n

    return (sum_pos - sum_neg), n_articles, best_ind, best_score, worst_ind, worst_score

def predict(list_articles, pipe):
    # takes in a list of articles and a classification pipeline object
    # and returns the sentiment calculated using calc_sentiment
    pred_dicts = pipe(list_articles)
    return calc_sentiment(pred_dicts)

@app.route("/")
def return_sentiment():
    todays_date = date.today().strftime("%b-%d-%y")
    ticker_articles = {}  # key=ticker name, val=list of strings (all news articles for the current day)
    finviz_url = "https://finviz.com/quote.ashx?t="
    # Start traversal with seed from file_with_seedURLs(https://eecs.engin.umich.edu/).

    session = requests.session()
    session.max_redirects = 4
    for ticker in ticker_list:
        ticker_articles[ticker] = []

        try:
            r = session.get(finviz_url + ticker, headers=headers, timeout=3)
        except:
            print('ERROR: Web site does not exist or too many redirects or timeout')
            continue

        html = BeautifulSoup(r.content, features='html.parser')
        ticker_articles = find_ticker_info(ticker, html, ticker_articles, todays_date)
        print("crawled:", ticker)

    print(ticker_articles)

    # Model time
    model = DistilBertForSequenceClassification.from_pretrained("BERTModel")
    tokenizer = DistilBertTokenizerFast.from_pretrained('distilbert-base-uncased')
    pipe = TextClassificationPipeline(model=model, tokenizer=tokenizer, return_all_scores=True)

    sentiments = {}

    for ticker in ticker_articles.keys():
        sent_score = predict(ticker_articles[ticker], pipe)
        print(ticker, sent_score)
        sentiments[ticker] = sent_score

    industry_dict = {}

    # converting sentiment info by article to by stock
    for industry in tickers.keys():
        industry_dict[industry] = {"avgScore":0, "stocks":{}}
        sum_score, sum_articles = 0.0, 0
        best_art, best_score, worst_art, worst_score = "", 0, "", 0

        for stock in tickers[industry]:
            sum_score += sentiments[stock][0]
            sum_articles += sentiments[stock][1]
            if sentiments[stock][1] == 0:
                industry_dict[industry]["stocks"][stock] = 0
            else:
                industry_dict[industry]["stocks"][stock] = sentiments[stock][0] / sentiments[stock][1]

            if sentiments[stock][3] > best_score:
                # absolute spaghetti but this should get the article for stock w/ highest sentiment
                best_art = ticker_articles[stock][sentiments[stock][2]]
                best_score = sentiments[stock][3]
            if sentiments[stock][5] < worst_score:
                worst_art = ticker_articles[stock][sentiments[stock][4]]
                worst_score = sentiments[stock][5]

        industry_dict[industry]["bestTitle"] = best_art
        industry_dict[industry]["worstTitle"] = worst_art
        if sum_articles > 0:
            industry_dict[industry]["avgScore"] = sum_score / sum_articles

    # return_data = {
    #     "Technology": {
    #         "avgScore": 0,
    #         "bestTitle": "",
    #         "worstTitle": "",
    #         "stocks": {
    #
    #         }
    #     },
    #     "Energy": {
    #         "avgScore": 0,
    #         "bestTitle": "",
    #         "worstTitle": "",
    #         "stocks": {
    #
    #         }
    #     },
    #     "Retail": {
    #         "avgScore": 0,
    #         "bestTitle": "",
    #         "worstTitle": "",
    #         "stocks": {
    #
    #         }
    #     },
    #     "Finance": {
    #         "avgScore": 0,
    #         "bestTitle": "",
    #         "worstTitle": "",
    #         "stocks": {
    #
    #         }
    #     }
    # }
    return_data = dumps(industry_dict)
    return_data = loads(return_data)
    print(return_data)

    for stock in sentiments:
        if stock in tickers["Technology"]:
            return_data["Technology"]["stocks"][stock] = sentiments[stock]
        elif stock in tickers["Energy"]:
            return_data["Energy"]["stocks"][stock] = sentiments[stock]
        elif stock in tickers["Retail"]:
            return_data["Retail"]["stocks"][stock] = sentiments[stock]
        else:
            return_data["Finance"]["stocks"][stock] = sentiments[stock]




    return return_data


if __name__ == "__main__":
    #app.run()
    res = return_sentiment()
    print("here")

# END MAIN