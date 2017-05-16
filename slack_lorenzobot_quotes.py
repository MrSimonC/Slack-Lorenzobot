import requests
import json
from bs4 import BeautifulSoup


def get_design_quote():
    url = 'http://quotesondesign.com/wp-json/posts?filter[orderby]=rand&filter[posts_per_page]=1'
    r = _get_json(url)
    quote = r[0]['content']
    quote = BeautifulSoup(quote, 'html.parser')
    return quote.text.strip() + ' - ' + r[0]['title']


def get_inspring_quote():
    url = 'http://api.forismatic.com/api/1.0/?method=getQuote&format=json&lang=en'
    quote = ''
    while True:
        try:
            quote = _get_json(url)
            break
        except json.decoder.JSONDecodeError:
            continue
    return quote['quoteText'].strip() + ' - ' + quote['quoteAuthor']


def _get_json(url):
    r = requests
    r = r.get(url)
    return json.loads(r.text)

if __name__ == '__main__':
    print(get_inspring_quote())
