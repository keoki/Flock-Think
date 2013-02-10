import os
import random
from dateutil.parser import parse
import urllib

from flask import Flask, request, redirect, url_for, render_template

import twittersentiment as ts

app = Flask(__name__)
#app.config.from_object = (__name__)
auth = ts.authenticate()

title = "FlockThink"

def trim_tweets(t, tl = 8):
    return t[:tl] if len(t) > tl else t 

def get_word(statsdict):
    """returns the approrpiate list of words, and colors for a sentiment between 0 (bad) and 1 (good)."""
    diff = statsdict['pct_pos'] - statsdict['pct_neg']
    if abs(diff) <= 10: # neither is significantly larger
        return ["so so", "alright", "okay", "meh"], "" # empty string keeps font color the same
    if diff < 0: # effectively < -10 (sad)
        if diff < -20: # really bad
            return ["terrible", "awful", "bad" ], "FF0083"
        else:
            return [ "poor", "icky", "smelly" ], "FF0083"
        
    else: # effectively diff > 10 (happy)
        if diff > 20: # really good
            return ["terrific", "awesome", "amazing", "fabulous", "phenomenal" ], "#67FF00"
        else: 
            return ["rad", "good", "sweet", "great"], "#67FF00"

@app.route('/')
def search_page():
    return render_template("index.html", title=title)

@app.route('/about')
def about():
    return render_template("about.html")

@app.route('/search/<term>')
def sbp(term):
    term = (urllib.unquote(term)).strip()
    pos, neg, top_pos, top_neg, neu = ts.search_get_sentiment(term, auth)

    stats = dict()
    stats['term'] = term
    stats['pos'] = len(pos)
    stats['neg'] = len(neg)
    stats['neu'] = len(neu)
    stats['sum'] = stats['pos'] + stats['neg'] + stats['neu']
    stats['top_pos'] = len(top_pos)
    stats['top_neg'] = len(top_neg)
    stats['pct_pos'] = int(100.0*stats['pos']/float(stats['sum']))
    stats['pct_neu'] = int(100.0*stats['neu']/float(stats['sum']))
    stats['pct_neg'] = int(100.0*stats['neg']/float(stats['sum']))

    # print stats
    words, color = get_word(stats)

    # trim top tweets down.  pos/neg are sorted by sentiment
    tweet_limit = 8

    pos = trim_tweets(pos, tweet_limit)
    neg = trim_tweets(neg, tweet_limit)

    for i, t in enumerate(pos):
        pos[i]['formatted_date'] = parse(t['created_at']).strftime("%B %d %Y")
        
    top_pos = [ (t[0], urllib.quote(t[0]), t[1]) for t in top_pos ]
    top_neg = [ (t[0], urllib.quote(t[0]), t[1]) for t in top_neg ]

    text = dict()
    text['term'] = term
    text['text_result'] = words[random.randint(0, len(words)-1)]
    text['color'] = color

    return render_template("results.html", pos=pos, pos_words=top_pos, neg=neg, neg_words=top_neg, stats=stats, text=text)

@app.route('/search', methods=['POST'])
def search():
    return redirect(url_for('sbp', term=request.form['search_text']))

if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    # app.debug = True
    app.run(host='0.0.0.0', port=port)
