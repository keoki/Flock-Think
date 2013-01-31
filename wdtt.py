import os
from flask import Flask, request, session, g, redirect, url_for, abort, \
     render_template, flash, _app_ctx_stack
import twittersentiment as ts

app = Flask(__name__)
#app.config.from_object = (__name__)
auth = ts.authenticate()

title = "What does Twitter think?"

@app.route("/")
def search_page():
    return render_template("index.html", title=title)

@app.route("/rawsearch", methods=['POST'])
def rawsearch():
    # should get (pos_score, neg_score, name, tweet)
    scores = ts.search_get_raw_sentiment(request.form['search_text'], auth)
    # scores = (pos, neg, raw_tweet)
    formatted_scores = []
    for (p, n, t) in scores:
        import pprint
        pprint.pprint(t)
        formatted_scores.append( (p, n, t['from_user'], t['text']))
    return render_template('results_raw.html', scores=scores)

@app.route("/search", methods=['POST'])
def search():
    # good, bad, irrelevant
    g, b, i = ts.search_get_sentiment(request.form['search_text'], auth)
    return render_template('results.html', good=g, bad=b, irr=i)

if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    app.debug = True
    app.run(port=port)
