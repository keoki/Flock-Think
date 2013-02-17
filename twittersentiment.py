import string
import re
import pickle
from Queue import Queue
import threading
import time

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

def get_tweet_page(term, page, auth):
    """ Uses the Twitter API to search for tweets. Gets 100 at a time. Returns
    a list of json dicts of tweets according to the search term.

    term - search term
    page - page to get
    auth - authorization. from twittersentiment.authenticate()
    """
    ts = twitter.Twitter(domain="search.twitter.com", auth=auth)

    # print "getting tweet page", page, term
    result = ts.search(q = term, page = page, lang = 'en', rpp = 100,
                    result_type = "recent", include_entities = 'true')
    # print page, "ZOMG!", result['results']
    return result['results']

class DocumentDownloader(threading.Thread):
    """ A class to download tweets from twitter. Basically you start the threads and dump pages to search for in the queue.

    Implementation from: https://gist.github.com/ghl3/4556336
    http://www.spontaneoussymmetry.com/blog/archives/445
    """
    
    def __init__(self, queue):
        threading.Thread.__init__(self)
        self._stop = threading.Event()
        self.articles = []
        self.queue = queue

    def stop(self):
        self._stop.set()

    def stopped(self):
        return self._stop.isSet()

    def get_articles(self):
        return self.articles

    def run(self):
        while True:
            if self.stopped():
                return
            if self.queue.empty(): 
                time.sleep(0.1)
                continue
            try:
                term, p, auth = self.queue.get()
                article = get_tweet_page(term, p, auth)
                self.articles.extend(article)
                # print "Successfully processed page: ", p,
                # print " by thread: ", self.ident
                # No need for a 'queue.task_done' since we're 
                # not joining on the queue
            except:
                print "Failed to process page: ", p

def search_tweets(term, limit=300, auth=None, num_threads=3):
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
    if limit < 100:
        print "limit %d is too small, resetting to 100" % limit
        limit = 100

    q = Queue()
    threads = []

    # Create the threads and 'start' them.
    # At this point, they are listening to the
    # queue, waiting to consume
    for i in xrange(num_threads):
        thread = DocumentDownloader(q)
        thread.setDaemon(True)
        thread.start()
        threads.append(thread)

    # We want to download one page for each namespace,
    # so we put every namespace in the queue, and
    # these will be processed by the threads
    for p in range(limit // fetchlimit):
        q.put((term, p+1, auth))

    # Wait for all entries in the queue
    # to be processed by our threads
    # One could do a queue.join() here, 
    # but I prefer to use a loop and a timeout
    while not q.empty():
        time.sleep(0.1)

    # Terminate the threads once our
    # queue has been fully processed
    for thread in threads:
        thread.stop()
    for thread in threads:
        thread.join()

    # except:
    #     print "Main thread hit exception"
    #     # Kill any running threads
    #     for thread in threads:
    #         thread.stop()
    #     for thread in threads:
    #         thread.join()
    #     raise

    # Collect all downloaded documents
    # from our threads
    result = []
    for thread in threads:
        # print "thread articles", type(thread.get_articles()), thread.get_articles()
        result.extend(thread.get_articles())

    return result
    #     
    # result = []
    # for p in range(limit // fetchlimit):
    #     result.exten( )
    #     r = ts.search(q=term,
    #                 result_type="recent",
    #                 rpp=fetchlimit,
    #                 page=p+1,
    #                 lang = lang,
    #                 include_entities = 'true')
    #     if len(r) == 0: # we have no results anymore. stop.
    #         return result
    #     result.extend( get_tweet_page(term, p+1, auth, result_type))

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

def remove_tweets(tweets, remove_rt = True):
    """ Remove tweets on criteria. Right now it just removes Retweets.
    """
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
    # t = [t['text'] for t in tweets]
    t = clean_tweets(tweets) # gives us a list of tweets that have been processed
    
    result = classifier.predict_proba(t)
    r = []
    for i, v in enumerate(result):
        r.append( (v[1], v[0], tweets[i]))

    return r

# These are regexps for clean_tweets()
t_username = re.compile('@([A-Za-z0-9_]+)')
t_url = re.compile('htt[p|ps]://t.co/[a-zA-Z0-9\-\.]{8}')
# from: http://stackoverflow.com/questions/4574509/python-remove-duplicate-chars-using-regex
t_repeated = re.compile('([a-z])\1{3,25}')
def clean_tweets(tweets):
    """Clean tweets from twitter and remove the usernames, urls and repeated letters.
    tweets is an iterable of tweet json objects
    """
    outlist = []
    # from: Twitter Sentiment Classification using Distant Supervision
    # 1: replace usernames with USERNAME
    # 2: replace url with URL
    # 3: replace repeated letters with two
    
    for t in tweets:
        # origtxt = t['text']
        # found_username = True if re.search(t_username, t['text']) else False
        # found_url = True if re.search(t_url, t['text']) else False
        rtext = re.sub(t_username, "USERNAME",  t['text'])
        # print rtext
        rtext = re.sub(t_url, "URL", rtext)

        # print rtext
        rtext = re.sub(r'([a-z])\1{2,25}', r'\1\1', rtext)

        # print "text!", rtext, t['text']
        outlist.append( rtext )

    return outlist

def sort_by_sentiment(tweets):
    """ Sorts tweets by sentiment.
    """
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

def search_get_sentiment(term, auth=None):
    raw = search_tweets(term, auth=auth)
    if len(raw) == 0: # No tweets :(
        return [], [], [], [], []

    filtered = remove_tweets(raw)
    pos, neu, neg = sort_by_sentiment(filtered)

    top_pos = get_top_words(pos, filter_term=term.lower())
    top_neg = get_top_words(neg, filter_term=term.lower())
    return pos, neg, top_pos, top_neg, neu
