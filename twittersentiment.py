import twitter
import sentiment
import pickle
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
    return get_raw_sentiment_sk(tweets)

def get_raw_sentiment_orig(tweets):
    """Get the raw sentiment from a tweet.  The sentiment factor returned is a pair of numbers whose sum is 1.  The first is the positive sentiment, and the second is the negative sentiment.
    Returns a list of tweets in the form (pos_sent, neg_sent, raw_tweet)
    """
    v = []
    for t in tweets:
        tokens = bag_of_words(t['text'].split())

        probs = classifier.prob_classify(tokens)
        pos, neg = probs.prob("pos"), probs.prob("neg")
        v.append( (pos, neg, t) )

    return v

def get_raw_sentiment_new(tweets):
    """Get the raw sentiment from a tweet.  The sentiment factor returned is a pair of numbers whose sum is 1.  The first is the positive sentiment, and the second is the negative sentiment.
    Returns a list of tweets in the form (pos_sent, neg_sent, raw_tweet)
    """
    v = []
    for t in tweets:
        features = sentiment.extract_words(t['text'])
        v.append( dict(zip(features, map(lambda a: True, features))) )
    result = classifier.batch_prob_classify(v)
    # print "result", result
    r = []
    # bug here: v is enumerated and set.  fix
    for i, v in enumerate(v):
        r.append( (result[i].prob("pos"), result[i].prob("neg"), tweets[i])) 
    return r

def get_raw_sentiment_sk(tweets):
    """Get the raw sentiment from a tweet.  The sentiment factor returned is a pair of numbers whose sum is 1.  The first is the positive sentiment, and the second is the negative sentiment.
    Returns a list of tweets in the form (pos_sent, neg_sent, raw_tweet)
    """
    t = [t['text'] for t in tweets]
    result = classifier.predict_proba(t)
    # print "result", result
    r = []
    for i, v in enumerate(result):
        r.append( (v[1], v[0], tweets[i]))
        print v[1], v[0], tweets[i]['text']
    # print r
    return r

def sort_by_sentiment(tweets):
    """ Sorts tweets by sentiment.
    """
    threshold = 0.5
    st = get_raw_sentiment(tweets)

    # rank the elements by score happy to sad.
    st.sort(reverse=True)
    pos = list()
    neg = list()
    [pos.append(t) if p > threshold else neg.append(t) for (p, n, t) in st]
    # reversing the negative ones puts the saddest at the top
    neg.reverse()

    return pos, neg
    
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
        if p > 0.66:
            pos.append(t)
        elif p > 0.33:
            neu.append(t)
        else:
            neg.append(t)

    # reversing puts negatives at the top.
    neg.reverse()

    return pos, neu, neg

def get_top(tweetlist, filter_term=None, filter_common = True, cutoff=3, remove_words_shorter_than=3):
    """get top words from tweet list.  Filter_term is used to remove terms from list (ie: search terms)
    cutoff - # of occurrences in order to call it good.
    filter_common = remove common words
    filter_term - other term to remove (ie: search term)
    remove_words_shorter_than - remove words shorter than or equal to this value
    """
    combined_tweets = norm_words(" ".join([t['text'] for t in tweetlist]))
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

def bag_of_words(words):
    return dict([(word, True) for word in words])

def norm_words(words, lower=True, remove_punctuation = True, remove_http = True):
    """normalize words by converting to lower case and removing punctuation. Works on both lists of words and a single string, but it's recommenede that this be used on a single string rather than lists of words since norm_words can make some strings empty and it does not remove them.
    """
    import string, operator, re

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
    pos,neu, neg = sort_by_sentiment(filtered)

    top_pos = get_top(pos, filter_term=term.lower())
    top_neg = get_top(neg, filter_term=term.lower())
    return pos, neg, top_pos, top_neg, neu
 