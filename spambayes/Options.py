# Options.options is a globally shared options object.

# XXX As this code is, option names must be unique across ini sections,
# XXX and must not conflict with OptionsClass method names.

import sys, os
import StringIO
import ConfigParser
from sets import Set

__all__ = ['options']

defaults = """
[Tokenizer]
# If true, tokenizer.Tokenizer.tokenize_headers() will tokenize the
# contents of each header field just like the text of the message
# body, using the name of the header as a tag.  Tokens look like
# "header:word".  The basic approach is simple and effective, but also
# very sensitive to biases in the ham and spam collections.  For
# example, if the ham and spam were collected at different times,
# several headers with date/time information will become the best
# discriminators.  (Not just Date, but Received and X-From_.)
basic_header_tokenize: False

# If true and basic_header_tokenize is also true, then
# basic_header_tokenize is the only action performed.
basic_header_tokenize_only: False

# If basic_header_tokenize is true, then basic_header_skip is a set of
# headers that should be skipped.
basic_header_skip: received
    date
    x-.*

# If false, tokenizer.Tokenizer.tokenize_body() strips HTML tags
# from pure text/html messages.  Set true to retain HTML tags in this
# case.  On the c.l.py corpus, it helps to set this true because any
# sign of HTML is so despised on tech lists; however, the advantage
# of setting it true eventually vanishes even there given enough
# training data.  If you set this true, you should almost certainly set
# ignore_redundant_html true too.
retain_pure_html_tags: False

# If true, when a multipart/alternative has both text/plain and text/html
# sections, the text/html section is ignored.  That's likely a dubious
# idea in general, so false is likely a better idea here.  In the c.l.py
# tests, it helped a lot when retain_pure_html_tags was true (in that case,
# keeping the HTML tags in the "redundant" HTML was almost certain to score
# the multipart/alternative as spam, regardless of content).
ignore_redundant_html: False

# Generate tokens just counting the number of instances of each kind of
# header line, in a case-sensitive way.
#
# Depending on data collection, some headers aren't safe to count.
# For example, if ham is collected from a mailing list but spam from your
# regular inbox traffic, the presence of a header like List-Info will be a
# very strong ham clue, but a bogus one.  In that case, set
# count_all_header_lines to False, and adjust safe_headers instead.

count_all_header_lines: False

# Like count_all_header_lines, but restricted to headers in this list.
# safe_headers is ignored when count_all_header_lines is true.

safe_headers: abuse-reports-to
    date
    errors-to
    from
    importance
    in-reply-to
    message-id
    mime-version
    organization
    received
    reply-to
    return-path
    subject
    to
    user-agent
    x-abuse-info
    x-complaints-to
    x-face

# A lot of clues can be gotten from IP addresses and names in Received:
# headers.  Again this can give spectacular results for bogus reasons
# if your test corpora are from different sources.  Else set this to true.
mine_received_headers: False

[TestDriver]
# These control various displays in class TestDriver.Driver, and Tester.Test.

# A message is considered spam iff it scores greater than spam_cutoff.
# If using Graham's combining scheme, 0.90 seems to work best for "small"
# training sets.  As the size of the training sets increase, there's not
# yet any bound in sight for how low this can go (0.075 would work as
# well as 0.90 on Tim's large c.l.py data).
# For Gary Robinson's scheme, 0.50 works best for *us*.  Other people
# who have implemented Graham's scheme, and stuck to it in most respects,
# report values closer to 0.70 working best for them.
spam_cutoff: 0.90

# Number of buckets in histograms.
nbuckets: 40
show_histograms: True

# Display spam when
#     show_spam_lo <= spamprob <= show_spam_hi
# and likewise for ham.  The defaults here don't show anything.
show_spam_lo: 1.0
show_spam_hi: 0.0
show_ham_lo: 1.0
show_ham_hi: 0.0

show_false_positives: True
show_false_negatives: False

# Near the end of Driver.test(), you can get a listing of the "best
# discriminators" in the words from the training sets.  These are the
# words whose WordInfo.killcount values are highest, meaning they most
# often were among the most extreme clues spamprob() found.  The number
# of best discriminators to show is given by show_best_discriminators;
# set this <= 0 to suppress showing any of the best discriminators.
show_best_discriminators: 30

# The maximum # of characters to display for a msg displayed due to the
# show_xyz options above.
show_charlimit: 3000

# If save_trained_pickles is true, Driver.train() saves a binary pickle
# of the classifier after training.  The file basename is given by
# pickle_basename, the extension is .pik, and increasing integers are
# appended to pickle_basename.  By default (if save_trained_pickles is
# true), the filenames are class1.pik, class2.pik, ...  If a file of that
# name already exists, it's overwritten.  pickle_basename is ignored when
# save_trained_pickles is false.

save_trained_pickles: False
pickle_basename: class

[Classifier]
# Fiddling these can have extreme effects.  See classifier.py for comments.
hambias: 2.0
spambias: 1.0

min_spamprob: 0.01
max_spamprob: 0.99
unknown_spamprob: 0.5

max_discriminators: 16

###########################################################################
# Speculative options for Gary Robinson's ideas.  These may go away, or
# a bunch of incompatible stuff above may go away.

# Use Gary's scheme for combining probabilities.
use_robinson_combining: False

# Use Gary's scheme for computing probabilities, along with its "a" and
# "x" parameters.
use_robinson_probability: False
robinson_probability_a: 1.0
robinson_probability_x: 0.5

# Use Gary's scheme for ranking probabilities.
use_robinson_ranking: False
"""

int_cracker = ('getint', None)
float_cracker = ('getfloat', None)
boolean_cracker = ('getboolean', bool)
string_cracker = ('get', None)

all_options = {
    'Tokenizer': {'retain_pure_html_tags': boolean_cracker,
                  'ignore_redundant_html': boolean_cracker,
                  'safe_headers': ('get', lambda s: Set(s.split())),
                  'count_all_header_lines': boolean_cracker,
                  'mine_received_headers': boolean_cracker,
                  'basic_header_tokenize': boolean_cracker,
                  'basic_header_tokenize_only': boolean_cracker,
                  'basic_header_skip': ('get', lambda s: Set(s.split())),
                 },
    'TestDriver': {'nbuckets': int_cracker,
                   'show_ham_lo': float_cracker,
                   'show_ham_hi': float_cracker,
                   'show_spam_lo': float_cracker,
                   'show_spam_hi': float_cracker,
                   'show_false_positives': boolean_cracker,
                   'show_false_negatives': boolean_cracker,
                   'show_histograms': boolean_cracker,
                   'show_best_discriminators': int_cracker,
                   'save_trained_pickles': boolean_cracker,
                   'pickle_basename': string_cracker,
                   'show_charlimit': int_cracker,
                   'spam_cutoff': float_cracker,
                  },
    'Classifier': {'hambias': float_cracker,
                   'spambias': float_cracker,
                   'min_spamprob': float_cracker,
                   'max_spamprob': float_cracker,
                   'unknown_spamprob': float_cracker,
                   'max_discriminators': int_cracker,
                   'use_robinson_combining': boolean_cracker,
                   'use_robinson_probability': boolean_cracker,
                   'robinson_probability_a': float_cracker,
                   'robinson_probability_x': float_cracker,
                   'use_robinson_ranking': boolean_cracker,
                   },
}

def _warn(msg):
    print >> sys.stderr, msg

class OptionsClass(object):
    def __init__(self):
        self._config = ConfigParser.ConfigParser()

    def mergefiles(self, fnamelist):
        self._config.read(fnamelist)
        self._update()

    def mergefilelike(self, filelike):
        self._config.readfp(filelike)
        self._update()

    def _update(self):
        nerrors = 0
        c = self._config
        for section in c.sections():
            if section not in all_options:
                _warn("config file has unknown section %r" % section)
                nerrors += 1
                continue
            goodopts = all_options[section]
            for option in c.options(section):
                if option not in goodopts:
                    _warn("config file has unknown option %r in "
                         "section %r" % (option, section))
                    nerrors += 1
                    continue
                fetcher, converter = goodopts[option]
                value = getattr(c, fetcher)(section, option)
                if converter is not None:
                    value = converter(value)
                setattr(options, option, value)
        if nerrors:
            raise ValueError("errors while parsing .ini file")

    def display(self):
        output = StringIO.StringIO()
        self._config.write(output)
        return output.getvalue()

options = OptionsClass()

d = StringIO.StringIO(defaults)
options.mergefilelike(d)
del d

alternate = os.getenv('BAYESCUSTOMIZE')
if alternate:
    options.mergefiles(alternate.split())
else:
    options.mergefiles(['bayescustomize.ini'])

