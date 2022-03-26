# Munnawn, uniqname: munnawng
# EECS 486 final project

# usage: python sentiment.py

from datetime import date
from bs4 import BeautifulSoup
import requests

ticker_list = ["TSLA", "NVDA", "AAPL", "AMD", "FB", "AMZN", "MSFT", "BABA", "GOOGL", "GOOG", "TLRY", "OXY", "NIO", "GME", "XOM", "SQ", "MU", "CVX", "INTC", "BAC", "HD"]
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

if __name__ == "__main__":
    todays_date = date.today().strftime("%b-%d-%y")
    ticker_articles = {} # key=ticker name, val=list of strings (all news articles for the current day)
    finviz_url = "https://finviz.com/quote.ashx?t="
    # Start traversal with seed from file_with_seedURLs(https://eecs.engin.umich.edu/).

    session = requests.session()
    session.max_redirects = 4
    for ticker in ticker_list:
        ticker_articles[ticker] = []
        
        try:
            r = session.get(finviz_url+ticker, headers = headers, timeout = 3)
        except:
            print('ERROR: Web site does not exist or too many redirects or timeout')
            continue

        html = BeautifulSoup(r.content, features='html.parser')
        ticker_articles = find_ticker_info(ticker, html, ticker_articles, todays_date)
        print("crawled:",ticker)
    
    print(ticker_articles)

# END MAIN