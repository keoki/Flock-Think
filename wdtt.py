import os
from flask import Flask, request, session, g, redirect, url_for, abort, \
     render_template, flash, _app_ctx_stack
import twittersentiment as ts
import random

app = Flask(__name__)
#app.config.from_object = (__name__)
auth = ts.authenticate()

title = "What does Twitter think?"

@app.route("/")
def search_page():
    return render_template("index.html", title=title)

# @app.route("/rawsearch", methods=['POST'])
# def rawsearch():
#     scores = ts.search_get_raw_sentiment(request.form['search_text'], auth)
# #    formatted_scores = [ (p, n, t['from_user'], t['text']) for (p, n, t) in scores ]
# #    pos, pos_word, neg, neg_words
#     return render_template('results_raw.html', scores=formatted_scores)


@app.route("/search", methods=['POST'])
def search():
    term = request.form['search_text']
    pos, neg, top_pos, top_neg = ts.search_get_sentiment(term, auth)
    p = [ (t['from_user'], t['text']) for t in pos]
    n = [ (t['from_user'], t['text']) for t in neg]

    pos_words = ["amazing", "good", "great", "awesome", "fabulous", "terrific", "rad", "sweet"]
    neg_words = ["terrible", "poor", "sucks", "smelly", "bad", "awful", "icky"]

    if len(pos) > len(neg):
        words = pos_words
        color = "#67FF00"
    else:
        words = neg_words
        color = "#FF0083"

    text = dict()
    text['term'] = term
    text['text_result'] = words[random.randint(0, len(words)-1)]
    text['color'] = color

#    print pos, top_pos
    stats = dict()
    stats['pos'] = len(pos)
    stats['neg'] = len(neg)
    stats['top_pos'] = len(top_pos)
    stats['top_neg'] = len(top_neg)

    return render_template("results.html", pos=p, pos_words=top_pos, neg=n, neg_words=top_neg, stats=stats, text=text)


if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    app.debug = True
    app.run(port=port)
