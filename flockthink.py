#!/usr/bin/env python
import os
import random
from dateutil.parser import parse
import urllib

from flask import Flask, request, redirect, url_for, render_template
import json

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
        return ["so so", "alright", "okay", "meh"], "C9CCFC" # empty string keeps font color the same
    if diff < 0: # effectively < -10 (sad)
        if diff < -20: # really bad
            return ["terrible", "awful", "bad" ], "FCB2AE"
        else:
            return [ "poor", "icky", "smelly", "abominable" ], "FCB2AE"
        
    else: # effectively diff > 10 (happy)
        if diff > 20: # really good
            return ["terrific", "awesome", "amazing", "fabulous", "phenomenal" ], "#ABFF83"
        else: 
            return ["rad", "good", "sweet", "great"], "#ABFF83"

def compare_terms(terms):
    """ Compares a list of terms by sentiment on twitter.  Returns a dictionary of terms with sentiment (pos, neg, neu, pct_pos, pct_neg, pct_neu)
    """
    result = dict()
    for t in terms:
        r = { "term": t }
        try:
            pos, neg, top_pos, top_neg, neu = ts.search_get_sentiment(t, auth)
            if len(pos) + len(neg) + len(neu) == 0:
                for s in ('pos', 'neg', 'neu'):
                    r[s] = []
                continue

        except ts.twitter.TwitterHTTPError:
            # Twitter Error!
            for s in ('pos', 'neg', 'neu'):
                r[s] = []
            continue
        
        r['pos'] = len(pos)
        r['neg'] = len(neg)
        r['neu'] = len(neu)
        r['sum'] = r['pos'] + r['neg'] + r['neu']
        r['pct_pos'] = int(100.0*r['pos']/float(r['sum']))
        r['pct_neu'] = int(100.0*r['neu']/float(r['sum']))
        r['pct_neg'] = int(100.0*r['neg']/float(r['sum']))
        r['top_pos'] = len(top_pos)
        r['top_neg'] = len(top_neg)

        try:
            ts.insert(r, pos+neg+neu)
        except:
            app.logger.error("Could not insert into database. Query was %s." % t)

        result[t] = r

    return result

@app.route('/')
def search_page():
    return render_template("index.html", title=title)

@app.route('/about')
def about():
    return render_template("about.html")

@app.route('/search/<term>')
def search_term(term):
    term = (urllib.unquote(term)).strip() # remove whitespace on edges
    if term.find(",") != -1:
        terms = term.split(",")
        terms = [t.strip() for t in terms]
        result = compare_terms(terms)
        return render_template("compare.html", result=result)

    try:
        pos, neg, top_pos, top_neg, neu = ts.search_get_sentiment(term, auth)
        if len(pos) + len(neg) + len(neu) == 0:
            return render_template("index.html", term=term)

    except ts.twitter.TwitterHTTPError:
        # Twitter Error!
        return render_template("error.html", term=term)

    stats = dict()
    stats['term'] = term
    stats['pos'] = len(pos)
    stats['neg'] = len(neg)
    stats['neu'] = len(neu)
    stats['sum'] = stats['pos'] + stats['neg'] + stats['neu']
    stats['pct_pos'] = int(100.0*stats['pos']/float(stats['sum']))
    stats['pct_neu'] = int(100.0*stats['neu']/float(stats['sum']))
    stats['pct_neg'] = int(100.0*stats['neg']/float(stats['sum']))
    stats['top_pos'] = len(top_pos)
    stats['top_neg'] = len(top_neg)

    try:
        ts.insert(stats, pos+neg+neu)
    except:
        app.logger.error("Could not insert into database. Query was %s." % term)
    
    # print stats
    words, color = get_word(stats)
    text = dict()
    text['term'] = term
    text['text_result'] = words[random.randint(0, len(words)-1)]
    text['color'] = color

    # trim top tweets down.  pos/neg are sorted by sentiment
    tweet_limit = 8
    pos = trim_tweets(pos, tweet_limit)
    neg = trim_tweets(neg, tweet_limit)
        
    top_pos = [ (t[0], urllib.quote(t[0]), t[1]) for t in top_pos ]
    top_neg = [ (t[0], urllib.quote(t[0]), t[1]) for t in top_neg ]

    return render_template("results.html", pos=pos, pos_words=top_pos, neg=neg, neg_words=top_neg, stats=stats, text=text)
@app.route('/cache/<term>')
def cache(term):
    print term
    return render_template("%s.html" % term)

@app.route('/api/<term>')
def api(term):
    term = (urllib.unquote(term)).strip()
    if term.find(",") != -1:
        terms = term.split(",")
        terms = [t.strip() for t in terms]
        result = compare_terms(terms)
        return json.dumps(result)

    stats = dict()
    stats['term'] = term
    
    try:
        pos, neg, top_pos, top_neg, neu = ts.search_get_sentiment(term, auth)
        if len(pos) + len(neg) + len(neu) == 0:
            stats['error'] = "No search results"
            return json.dumps({term: stats})

    except ts.twitter.TwitterHTTPError:
        # Twitter Error!
        stats['error'] = "Could not connect to twitter"
        return json.dumps({term: stats})

    stats['pos'] = len(pos)
    stats['neg'] = len(neg)
    stats['neu'] = len(neu)
    stats['sum'] = stats['pos'] + stats['neg'] + stats['neu']
    stats['pct_pos'] = int(100.0*stats['pos']/float(stats['sum']))
    stats['pct_neu'] = int(100.0*stats['neu']/float(stats['sum']))
    stats['pct_neg'] = int(100.0*stats['neg']/float(stats['sum']))

    try:
        ts.insert(stats, pos+neg+neu)
    except:
        pass

    # to be consistent with the multi-search, we must return a dict that looks like: { 'term': stats }
    return render_template("json.html", json=json.dumps({term: stats}))

@app.route('/search', methods=['POST'])
def search():
    return redirect(url_for('search_term', term=request.form['search_text']))

if __name__ == "__main__":
    # app.debug = True
    import logging
    file_handler = logging.FileHandler(os.path.expanduser("~/flask.log"))
    file_handler.setLevel(logging.WARNING)
    app.logger.addHandler(file_handler)

    port = int(os.environ.get('PORT', 5000))
    # app.run(host='0.0.0.0', port=port)
