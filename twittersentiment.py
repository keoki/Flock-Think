import twitter
from senti_classifier import senti_classifier as sc
import pickle

cl = "/Volumes/Haoma/keoki/datascience/insight-product/repos/sentiment_classifier/src/senti_classifier/classifier-NaiveBayes.tweets.pickle"
cl = "/scratch/classifier-NaiveBayes.tweets.pickle"
with open(cl, 'r') as f:
    classifier = pickle.load(f)

def authenticate():
    OAUTH_TOKEN="167133966-EnnTYkbphBbmwo9FFd2hwv5JSkOaNSRSBsh4LzY"
    OAUTH_SECRET="1Hni2nPVHjr5IPa7kqZUx5EnL14MjSvIvzkDhOiggK4"
    CONSUMER_KEY = "IeREJaWROxAO7olEYLiQ"
    CONSUMER_SECRET = "I0EVikHnnGU6wAzL7gl1nNuejIu2YuUiheleG7DtQIY"
    return twitter.OAuth(OAUTH_TOKEN, OAUTH_SECRET, CONSUMER_KEY, CONSUMER_SECRET)

def search_tweets(term, auth=None, result_type="recent", limit=9):
    """ Uses the Twitter API to search for tweets.  Returns a json dict of
    tweets according to the search term.
    """
    if not auth:
        auth = authenticate()
    if limit > 100:
        print "limit %d is too large, resetting to 100" % limit
        limit = 100

    ts = twitter.Twitter(domain="search.twitter.com", auth=auth)
    return ts.search(q=term,
                    result_type="recent",
                    limit=limit,
                    include_entities = 'true')['results']

def filter_tweets(tweets, remove_rt = False, lang='en'):
    """ filter tweets on criteria. Can either remove if retweet or remove based on lanuage.
    lang='all' does not do any removal based off lanuage
    """
    import re
    if remove_rt:
        rt_regex = re.compile("RT|[Rr]etweet")
    else:
        rt_regex = None

#    print len(tweets)

    for t in tweets:
#        print "tweet", t['text'], t['iso_language_code']
        if rt_regex:
            if re.search(rt_regex, t['text']):
#                print "removing on retweet:", t['text']
                tweets.remove(t)
                continue
        if lang != 'all':
            if t['iso_language_code'] != lang:
#                print "removing on language: ", t['iso_language_code']
                tweets.remove(t)
                continue

#    print len(tweets)
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

def sort_by_sentiment(tweets, threshold):
    """ Sorts tweets by sentiment
    """
    st = get_raw_sentiment(tweets)

def bag_of_words(words):
    return dict([(word, True) for word in words])

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
    tw = filter_tweets(tw, remove_rt=True)
    return get_raw_sentiment(tw)
    