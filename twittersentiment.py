import twitter
from senti_classifier import senti_classifier as sc
import pickle
import nltk
from nltk.corpus import stopwords

cl = "/Volumes/Haoma/keoki/datascience/insight-product/repos/sentiment_classifier/src/senti_classifier/classifier-NaiveBayes.tweets.pickle"
cl = "/scratch/classifier-NaiveBayes.tweets.pickle"
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
                ol = len(tweets)
                tweets.remove(t)
                nl = len(tweets)
                print 'RT remove:', t['text'], ol, nl
                continue
            else:
                print t['text']
    return tweets

def get_raw_sentiment(tweets):
    """Get the raw sentiment from a tweet.  The sentiment factor returned is a pair of numbers whose sum is 1.  The first is the positive sentiment, and the second is the negative sentiment.
    Returns a list of tweets in the form (pos_sent, neg_sent, raw_tweet)
    """
    v = []
    for t in tweets:
        # print pprint.pprint(t)
        tokens = bag_of_words(t['text'].split())

        probs = classifier.prob_classify(tokens)
        pos, neg = probs.prob("pos"), probs.prob("neg")
        v.append( (pos, neg, t) )

    return v

def sort_by_sentiment(tweets):
    """ Sorts tweets by sentiment
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

def get_top(tweetlist, filter_term=None, filter_common = True, cutoff=5):
    """get top words from tweet list.  Filter_term is used to remove terms from list (ie: search terms)
    cutoff - # of occurrences in order to call it good.
    
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

    print words
    if type(words) == str:
        if remove_http:
            words = re.sub(http_str, "", words)
        if lower:
            words = words.lower()
        if remove_punctuation:
            table = string.maketrans(sp, " "*len(sp))
            words = words.translate(table)
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

def get_sentiment(tweets):
    """
    """
    # for now, make 3 categories for tweets, 1: good, 2: bad, 3: irrelevant
    good = []
    bad = []
    irrelevant = []
    for i, t in enumerate(tweets, start=1):
        idx = i % 3
        v = (t['from_user'], t['text'])
        if idx == 0:
            good.append(v)
        elif idx == 1:
            bad.append(v)
        else: # idx == 2
            irrelevant.append(v)
    return good, bad, irrelevant

def search_get_sentiment(term, auth=None):
    return get_sentiment(search_tweets(term, auth=auth))

def search_get_raw_sentiment(term, auth=None):
    tw = search_tweets(term, auth=auth)
    tw = remove_tweets(tw, remove_rt=True)
    return get_raw_sentiment(tw)

def search_get_sentiment(term, auth=None):
    raw = search_tweets(term, auth=auth)
    filtered = remove_tweets(raw)
    pos, neg = sort_by_sentiment(filtered)

    top_pos = get_top(pos, filter_term=term.lower())
    top_neg = get_top(neg, filter_term=term.lower())
    return pos, neg, top_pos, top_neg
 