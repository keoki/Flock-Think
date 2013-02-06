import pickle
from nltk.corpus import stopwords
from nltk.stem import PorterStemmer
from nltk.tokenize import WordPunctTokenizer
from nltk.collocations import BigramCollocationFinder
from nltk.metrics import BigramAssocMeasures
from nltk.classify import NaiveBayesClassifier, MaxentClassifier
#from nltk.classify.util import accuracy

def extract_words(text):
    """Extract word tokens from a text.
    """
    stemmer = PorterStemmer()
    tokenizer = WordPunctTokenizer()
    tokens = tokenizer.tokenize(text)

    bigram_finder = BigramCollocationFinder.from_words(tokens)
    bigrams = bigram_finder.nbest(BigramAssocMeasures.chi_sq, 500)
    for bigram_tuple in bigrams:
        x = "%s %s" % bigram_tuple
        tokens.append(x)
    result =  [stemmer.stem(x.lower()) for x in tokens if x not in stopwords.words('english') and len(x) > 1]
    return result

def get_feature(word):
    return dict([(word, True)])

def bag_of_words(words):
    return dict([(word, True) for word in words])

def create_training_dict(text, sense):
    tokens = extract_words(text)
    return [(bag_of_words(tokens), sense)]

def get_train_set(texts):
    #Change to buffer `texts`
    train_set = []
    for sense, file in texts.iteritems():
        print "training %s " % sense
        text = open(file, 'r').read() #Change later
        features = extract_words(text)
        train_set = train_set + [(get_feature(word), sense) for word in features]
    return train_set
