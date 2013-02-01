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

@app.route('/')
def search_page():
    return render_template("index.html", title=title)

# @app.route("/rawsearch", methods=['POST'])
# def rawsearch():
#     scores = ts.search_get_raw_sentiment(request.form['search_text'], auth)
# #    formatted_scores = [ (p, n, t['from_user'], t['text']) for (p, n, t) in scores ]
# #    pos, pos_word, neg, neg_words
#     return render_template('results_raw.html', scores=formatted_scores)
def trim_tweets(t, tl = 8):
    return t[:tl] if len(t) > tl else t 

@app.route('/search/<term>')
def sbp(term):
    term = urllib.unquote(term)
    pos, neg, top_pos, top_neg = ts.search_get_sentiment(term, auth)

    stats = dict()
    stats['pos'] = len(pos)
    stats['neg'] = len(neg)
    stats['top_pos'] = len(top_pos)
    stats['top_neg'] = len(top_neg)


    pos_words = ["amazing", "good", "great", "awesome", "fabulous", "terrific", "rad", "sweet"]
    neg_words = ["terrible", "poor", "smelly", "bad", "awful", "icky"]
    neu_words = ["so so", "alright", "okay"]

    if len(pos) > len(neg):
        words = pos_words
        color = "#67FF00"
    elif len(pos) == len(neg):
        words = neu_words
        color = "#FFFFFF"
    else:
        words = neg_words
        color = "#FF0083"

    # trim top tweets down.  pos/neg are sorted by sentiment
    tweet_limit = 8
    print "pos before", len(pos)
    pos = trim_tweets(pos, tweet_limit)
    neg = trim_tweets(neg, tweet_limit)
    print "pos after", len(pos)
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
    app.run(port=port)
