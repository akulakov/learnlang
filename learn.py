#!/usr/bin/env python
from glob import glob
import nltk
import shelve, string
from time import time
import sys, itertools
from google.cloud import translate
from collections import defaultdict, Counter
from random import random

"""
TODO: stop translating after N number of translations per text for same word, e.g. 50?
"""
header = '''<html>
<head>
<meta charset="UTF-8"/>
</head>
<body><style>
.noun {color: hsl(120, 100%, 25%)}
.sentence {color: hsl(120, 100%, 20%)}
.tooltip {
    position: relative;
    display: inline-block;
    border-bottom: 0px dotted black;
}
.tooltip .tooltiptext {
    visibility: hidden;
}
.tooltip .tooltiptext {
    visibility: hidden;
    width: 120px;
    background-color: black;
    color: #fff;
    text-align: center;
    padding: 5px 0;
    border-radius: 6px;

    /* Position the tooltip text - see examples below! */
    position: absolute;
    z-index: 1;
    bottom: 100%;
    left: 50%;
    margin-left: -60px; /* Use half of the width (120/2 = 60), to center the tooltip */
}
.tooltip:hover .tooltiptext {
    visibility: visible;
}
</style>
         '''


target_language = 'es'
target_types = ['NN', 'NNS']
perc = 1
single_word_perc = 0.2
argv=sys.argv
del argv[0]
make_index = False

def create_index():
    with open('index.html', 'w') as fp:
        lst = [fn for fn in glob('*.html') if fn!='index.html']
        old = glob('old/*.html')
        tpl = '<html><body>{}</body></html>'
        fntpl = '<li><a href="{}">{}</a></li>'
        out = ['<h3>Main List</h3>', '<ul>']
        for fn in lst:
            out.append(fntpl.format(fn, fn))
        out.append('</ul><h3>OLD</h3><ul>')
        for fn in old:
            out.append(fntpl.format(fn, fn))
        out.append('</ul>')
        fp.write(tpl.format('\n'.join(out)))

if '-fr' in argv:
    target_language = 'fr'
    argv.remove('-fr')
if '-ru' in argv:
    target_language = 'ru'
    argv.remove('-ru')
if '-en' in argv:
    target_language = 'en'
    argv.remove('-en')
if '-vbp' in argv:
    target_types = ['VBP']
if '-vb' in argv:
    target_types = ['VB']
if '-nns' in argv:
    target_types = ['NNS']
if '-jj' in argv:
    target_types = ['JJ']
if '-ind' in argv:
    create_index()
    sys.exit()

for x in argv:
    if x.startswith('-perc'):
        perc = float(x[5:])

print("perc", perc)
print("single_word_perc", single_word_perc)

test_mode = '-test' in argv

quote = '’'
start_quote = '‘'
c_start = time()

ch_name = argv[0]
if ch_name.lower().endswith('.txt'):
    ch_name = ch_name[:-4]
chapter = open('%s.txt' % ch_name).read().split('\n\n')
client = translate.Client()
data = shelve.open('data')
cache = data.get('cache', {})
if target_language not in cache:
    cache[target_language] = {}
lookup = cache[target_language]
skip_words = ['ll', 'don', 'can', 'isn', 'wouldn', 'haven', 'shouldn', 'didn', 'doesn'
              ]

# for w_s, trans in list(lookup.items())[:100]:
#     # if len(w_s) > 25:
#     assert w_s == trans['input']
#     print(w_s,trans,'\n\n')
# sys.exit()

skip_words_by_target = dict(es=[
    'sun',      # translated as Dom for 'domingo'=sunday
    'kind',     # translated as tipo which is often wrong
    'look',     # mira - wrong when used as noun, or used in combinations like 'look after'?
    'way',      # camino - wrong when used as "the way I did it", etc?
    'fall',     # otono - wrong when used as in 'fall down'
    'saw',      # sierra
    'lay',      # laico
    'left',     # izquierda
    'stout',    # cerveza negro
    'door',     # por ??
    'fit',      # ajuste (as in apoplectic fit)
    'set',      # conjunto (as in a game set)
    'watch',    # reloj as in pocket watch


    # TEMP
    'small','other','same','high','low','big','little','large'
])

if target_language in skip_words_by_target:
    skip_words.extend(skip_words_by_target[target_language])

n_cached_trans = [0,0]

freq_table = Counter()
ignore_n = [0]

def getitem(seq, n):
    try: return seq[n]
    except IndexError:
        return None

ignore_type = 'IGNORE'
def make_trans_list(chapter):
    for n, par in enumerate(chapter):
        text = nltk.word_tokenize(par)
        tups = nltk.pos_tag(text)
        lst = []
        for n, (w, tp) in enumerate(tups):
            # if test_mode and 100 <= n <= 400 and "'" in w:
            if test_mode and w=='couldn':
                print(w, tp)
                next = getitem(tups,n+1)
                print("next", next)
            next = getitem(tups, n+1)
            next2 = getitem(tups, n+2)
            if len(w) <= 2:
                tp = ignore_type
            if next and next[0] in ("n't", "'t"):
                tp = ignore_type
            if next2 and next2[0] == 't':
                tp = ignore_type
            if random() > perc:
                tp = ignore_type
                ignore_n[0]+=1
                if ignore_n[0]<20:
                    print('ignoring', w)
            lst.append((w,tp))

        for w,tp in lst:
            if not test_mode and tp in target_types and w[0] in string.ascii_letters and w not in skip_words:
                yield w

def get_n_uncached(words, wdict=None, n=128):
    lst = []
    # import pdb;pdb.set_trace()
    while 1:
        if n<=0 or not words:
            break
        w = words.pop()
        if w in lookup:
            if wdict:
                wdict[w] = lookup[w]
            n_cached_trans[0] += 1
            freq_table[lookup[w]['translatedText']] += 1
        else:
            lst.append(w)
            n-=1
            n_cached_trans[1] += 1
    return lst

def translate(words):
    wdict = {}

    while 1:
        batch = get_n_uncached(words, wdict)
        if not batch:
            break
        bdict = dict(zip(batch, client.translate(batch, source_language='en', target_language=target_language)))
        for w in bdict.values():
            freq_table[w['translatedText']] += 1
        lookup.update(bdict)
        wdict.update(bdict)
    return wdict

def grouper(iterable, n, fillvalue=None):
    "Collect data into fixed-length chunks or blocks - recipe from itertools docs."
    # grouper('ABCDEFG', 3, 'x') --> ABC DEF Gxx"
    args = [iter(iterable)] * n
    return itertools.zip_longest(*args, fillvalue=fillvalue)

def main(chapter):
    words = list(make_trans_list(chapter))
    if test_mode:
        return
    wdict = translate(words)

    # with open('/Users/ak/projects/learnlang/%s.html' % ch_name, 'w') as fp:
    ttypes = '_'.join(target_types)
    fname = '%s_%s_%s.html' % (ch_name, target_language, ttypes)
    with open(fname, 'w') as fp:
        fp.write(header)

        paragraphs = []
        sentences = []
        for n, par in enumerate(chapter):
            out = []
            i = par.rfind('.')
            sentence = None
            if 40 <= (len(par) - i) <= 160:
                sentence = Sentence(par[i+1:])
                par = par[:i+1]
                sentences.append(sentence)

            text = [[nltk.word_tokenize(w), ' '] for w in par.split()]
            text = [x for sl in text for x in sl]
            tups = [nltk.pos_tag(x) for x in text]
            tups = [x for sl in tups for x in sl]


            for m, (w,tp) in enumerate(tups):
                next = getitem(tups, m+1)
                next2 = getitem(tups, m+2)
                if w == 'doesn':
                    print("w", w)
                    print("next", next)
                    print("next2", next2)
                    print()
                if next and next[0] in ("n't", "'t"):
                    tp = ignore_type
                if next2 and next2[0] == 't':
                    tp = ignore_type

                if random()<single_word_perc and tp in target_types and len(w)>2 and w[0] in string.ascii_letters:
                    tpl = '<span class="tooltip noun">{}<span class="tooltiptext">{}</span></span>'
                    if w in lookup:
                        out.append(tpl.format(lookup[w]['translatedText'], w))
                    else:
                        out.append(w)
                else:
                    out.append(w)
            if sentence:
                out.append(sentence)

            paragraphs.append(out)

        sentence_dict = translate([s.s for s in sentences])

        for paragraph in paragraphs:
            processed = []
            for w in paragraph:
                if isinstance(w, Sentence):
                    tpl = '<span class="tooltip sentence">{}<span class="tooltiptext">{}</span></span>'
                    # import pdb;pdb.set_trace()

                    processed.append(tpl.format(lookup[w.s]['translatedText'], w.s))
                else:
                    processed.append(w)
            fp.write('<p>' + ''.join(processed).replace('&#39;', quote).replace('``', '"').replace("''", '"') + '</p>\n\n')
            print('\r{}/{}'.format(n+1, len(chapter)), end=' '*20)
            sys.stdout.flush()
        fp.write('</body></html>')
    print('written: {} ...'.format(fname))
    print('total {}'.format(int(time()-c_start)))
    data['cache'] = cache
    data.close()
    print("n_cached_trans", n_cached_trans)
    print('20 most common')
    for word, n in freq_table.most_common(20):
        print(n, '   ', word)
    create_index()

class Sentence:
    def __init__(self, s):
        self.s=s
    def __repr__(self):
        return '<Sentence: {}>'.format(self.s)

main(chapter)
