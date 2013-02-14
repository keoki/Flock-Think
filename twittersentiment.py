import string
import operator
import re
import pickle

import twitter
import MySQLdb as mysqldb
import nltk
from nltk.corpus import stopwords

cl = "model.pickle" # currently a bayes classifier from 04-classifier2.py
try:
    classifier
except NameError:
    with open(cl, 'r') as f:
        classifier = pickle.load(f)

stopwords = stopwords.words("english")
# stopwords.append("via")
# stopwords.append("rt")
# stopwords.append("RT")

def authenticate():
    OAUTH_TOKEN="167133966-EnnTYkbphBbmwo9FFd2hwv5JSkOaNSRSBsh4LzY"
    OAUTH_SECRET="1Hni2nPVHjr5IPa7kqZUx5EnL14MjSvIvzkDhOiggK4"
    CONSUMER_KEY = "IeREJaWROxAO7olEYLiQ"
    CONSUMER_SECRET = "I0EVikHnnGU6wAzL7gl1nNuejIu2YuUiheleG7DtQIY"
    return twitter.OAuth(OAUTH_TOKEN, OAUTH_SECRET, CONSUMER_KEY, CONSUMER_SECRET)

def search_tweets(term, auth=None, result_type="recent", limit=300, lang='en'):
    """ Uses the Twitter API to search for tweets.  Returns a list of json 
    dicts of tweets according to the search term.
    """
    if not auth:
        auth = authenticate()

    # it's not clear from the twitter API if page works with rpp != 100, so for now force rpp/fetchlimit 100.  This means we can only request pages of 100 at a time.
    fetchlimit = 100
    if limit % fetchlimit != 0:
        print "limit %d not a multiple of 100, rounding to nearest" % limit
        limit = fetchlimit * int(round(float(limit) / fetchlimit))

    if limit > 1500:
        print "limit %d is too large, resetting to 1500" % limit
        limit = 1500

    ts = twitter.Twitter(domain="search.twitter.com", auth=auth)

    result = []
    for p in range(limit // fetchlimit):
        result.extend( ts.search(q=term,
                    result_type="recent",
                    rpp=fetchlimit,
                    page=p+1,
                    lang = lang,
                    include_entities = 'true')['results'])
    return result

def insert(query_with_sent, tweets_with_sent):
    """ Insert a query and sentiment information into the database.
    tweets_with_sent is a list of tweet objects, with tweet['sentiment_score'] as the sentiment score (this is set in sort_by_sentiment()).
    query_with_sent is a dictionary of the search term along with the number of positive/negative/neutral tweets.
    """
    # this is not optimal but we're low traffic so make a new connection every function call
    conn = mysqldb.connect(user="flask", passwd="m-Zbonkp5NXZHqZS nCAw5oXS8RR6aqzjDP3tiCg5cYPR36MK_z3u QvFMB8M4uY", db="insight")
    # Quote out search term.  This is the only input from the user so it's the only thing that needs to be quoted out.
    query_with_sent['term'] = conn.escape_string(query_with_sent['term'])

    sql = """INSERT INTO querylogs (search_term, time, num_pos, num_neg, num_neu)
		VALUES("{term}", NOW(), {pos}, {neg}, {neu});
    set @KEY = LAST_INSERT_ID();
    INSERT INTO tweets (query_id, tweet_id, twitter_id, sentiment) VALUES 
    """.format(**query_with_sent)

    for tweet in tweets_with_sent:
        sql += "(@KEY, {id}, {from_user_id}, {sentiment_score}),\n".format(**tweet)
    sql = sql[:-2] + ';\n'

    cur = conn.cursor()
    cur.execute(sql)
    cur.close()
    conn.commit()
    conn.close()
    return sql

def remove_tweets(tweets, remove_rt = True ):
    """ filter tweets on criteria. Right now it just removes Retweets.
    """
    import re
    if remove_rt:
        rt_regex = re.compile("RT|[Rr]etweet|RETWEET")
    else:
        return tweets

    for t in tweets:
        if rt_regex:
            if re.search(rt_regex, t['text']):
                tweets.remove(t)
    return tweets

def get_raw_sentiment(tweets):
    """Get the raw sentiment from a tweet.  The sentiment factor returned is a pair of numbers whose sum is 1.  The first is the positive sentiment, and the second is the negative sentiment.
    Returns a list of tweets in the form (pos_sent, neg_sent, raw_tweet)
    """
    t = [t['text'] for t in tweets]
    result = classifier.predict_proba(t)
    # print "result", result
    r = []
    for i, v in enumerate(result):
        r.append( (v[1], v[0], tweets[i]))
        # print v[1], v[0], tweets[i]['text']
    # print r
    return r
    
def sort_by_sentiment(tweets):
    """ Sorts tweets by sentiment.
    """
    threshold = 0.5
    st = get_raw_sentiment(tweets)

    st.sort(reverse=True)
    pos = []
    neu = []
    neg = []
    for (p, n, t) in st:
        t['sentiment_score'] = p # this is added so insert() can see the score
        if p > 0.66:
            pos.append(t)
        elif p > 0.33:
            neu.append(t)
        else:
            neg.append(t)

    # reversing puts negatives at the top.
    neg.reverse()

    return pos, neu, neg

def get_top_words(tweetlist, filter_term=None, filter_common = True, cutoff=3, remove_words_shorter_than=3):
    """get top words from tweet list.  Filter_term is used to remove terms from list (ie: search terms)
    cutoff - # of occurrences in order to call it good.
    filter_common = remove common words
    filter_term - other term to remove (ie: search term)
    remove_words_shorter_than - remove words shorter than or equal to this value
    """
    combined_tweets = norm_words(" ".join([t['text'] for t in tweetlist]))
    # remove the quotations from the filter_term.  Probably should make this more general but I cannot figure out string.translate()
    # http://stackoverflow.com/questions/265960/best-way-to-strip-punctuation-from-a-string-in-python
    filter_term = filter_term.replace("\"", "")
    combined_tweets = combined_tweets.replace(filter_term, "")
    if filter_common:
        combined_tweets = filter(lambda w: not w in stopwords, combined_tweets.split())
    else:
        combined_tweets = combined_tweets.split()
    # possible use 2-grams to get top as well.
    cutoff_combined = list()
    for keyword, count in nltk.FreqDist(combined_tweets).iteritems():
        if count >= cutoff:
            if len(keyword) <= remove_words_shorter_than:
                continue
            if keyword != filter_term:
                cutoff_combined.append((keyword, count))
    return cutoff_combined

def norm_words(words, lower=True, remove_punctuation = True, remove_http = True):
    """normalize words by converting to lower case and removing punctuation. Works on both lists of words and a single string, but it's recommenede that this be used on a single string rather than lists of words since norm_words can make some strings empty and it does not remove them.
    """

    http_str = re.compile('htt[p|ps]://t.co/[a-zA-Z0-9\-\.]{8}')   
    # for now, keep the @ and # since they're special to twitter
    sp = string.punctuation.replace("#","").replace("@","")

    # convert to string for normalize.
    if type(words) == unicode:
        words = words.encode("ascii", errors="ignore")

    # print words
    if type(words) == str:
        # print words
        if remove_http:
            words = re.sub(http_str, "", words)
        # print words
        if lower:
            words = words.lower()
        # print words
        if remove_punctuation:
            table = string.maketrans(sp, " "*len(sp))
            words = words.translate(table)
        # print words
    elif type(words) in (list, tuple):
        if remove_http:
            words = [re.sub(http_str, "", w) for w in words]
        if lower:
            words = [w.lower() for w in words]
        if remove_punctuation:
            table = string.maketrans(sp, " "*len(sp))
            words = [w.translate(table) for w in words]
    else:
        print "not list or string, not normalizing"

    # print words
    return words

def search_get_raw_sentiment(term, auth=None):
    tw = search_tweets(term, auth=auth)
    tw = remove_tweets(tw, remove_rt=True)
    return get_raw_sentiment(tw)

def search_get_sentiment(term, auth=None):
    raw = search_tweets(term, auth=auth)
    filtered = remove_tweets(raw)
    pos, neu, neg = sort_by_sentiment(filtered)

    cutoff_pct = 0.10
    top_pos = get_top_words(pos, filter_term=term.lower(), cutoff=int(cutoff_pct*len(pos)))
    top_neg = get_top_words(neg, filter_term=term.lower(), cutoff=int(cutoff_pct*len(neg)))
    return pos, neg, top_pos, top_neg, neu
