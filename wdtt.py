import os
from flask import Flask, request, session, g, redirect, url_for, abort, \
     render_template, flash, _app_ctx_stack
import twittersentiment as ts
import random
import urllib

app = Flask(__name__)
#app.config.from_object = (__name__)
auth = ts.authenticate()

title = "What does Twitter think?"

def trim_tweets(t, tl = 8):
    return t[:tl] if len(t) > tl else t 

def get_word(sent_pct):
    """returns the approrpiate list of words, and colors for a sentiment between 0 (bad) and 1 (good)."""
    if sent_pct > 0.8:
        return ["terrific", "awesome", "amazing", "fabulous" ], "#67FF00"
    elif sent_pct > 0.6:
        return ["rad", "good", "sweet", "great"], "#67FF00"
    elif sent_pct > 0.4:
        return ["so so", "alright", "okay"], "#000000"
    elif sent_pct > 0.2:
        return [ "poor", "icky", "smelly" ], "FF0083"
    else:
        return ["terrible", "awful", "bad" ], "FF0083"

@app.route('/')
def search_page():
    return render_template("index.html", title=title)

@app.route('/about')
def about():
    return render_template("about.html")

@app.route('/search/<term>')
def sbp(term):
    term = urllib.unquote(term)
    pos, neg, top_pos, top_neg = ts.search_get_sentiment(term, auth)

    stats = dict()
    stats['pos'] = len(pos)
    stats['neg'] = len(neg)
    stats['top_pos'] = len(top_pos)
    stats['top_neg'] = len(top_neg)
    stats['pct_pos'] = int(100.0*stats['pos']/float(stats['pos'] + stats['neg']))
    stats['pct_neg'] = 100 - stats['pct_pos']

    words, color = get_word(stats['pct_pos']/100.0)

    # trim top tweets down.  pos/neg are sorted by sentiment
    tweet_limit = 8
    # print "pos before", len(pos)
    pos = trim_tweets(pos, tweet_limit)
    neg = trim_tweets(neg, tweet_limit)
    # print "pos after", len(pos)
    p = [ (t['from_user'], t['text']) for t in pos]
    n = [ (t['from_user'], t['text']) for t in neg]

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
    app.debug = True
    app.run(host='0.0.0.0', port=port)
