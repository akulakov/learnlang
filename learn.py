#!/usr/bin/env python
import nltk
import shelve, string
from time import time
import sys, itertools
from google.cloud import translate
from collections import defaultdict, Counter

"""
TODO: stop translating after N number of translations per text for same word, e.g. 50?
"""

target_language = 'es'
target_types = ['NN', 'NNS']
argv=sys.argv
del argv[0]
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


    # TEMP
    # 'small','other','same','high','low','big','little','large'
])

if target_language in skip_words_by_target:
    skip_words.extend(skip_words_by_target[target_language])

n_cached_trans = [0,0]

freq_table = Counter()

def getitem(seq, n):
    try: return seq[n]
    except IndexError:
        return None


def make_trans_list(chapter):
    for n, par in enumerate(chapter):
        text = nltk.word_tokenize(par)
        tups = nltk.pos_tag(text)
        lst = []
        for n, (w, tp) in enumerate(tups):
            if test_mode and 100 <= n <= 120 and "'" in w:
                print(w, tp)
            next = getitem(tups, n+1)
            if next and next[0] == "n't":
                tp = 'IGNORE'
            lst.append((w,tp))

        for w,tp in lst:
            if not test_mode and tp in target_types and w[0] in string.ascii_letters and w not in skip_words:
                yield w

def get_n_uncached(words, wdict, n=128):
    lst = []
    while 1:
        if n<=0 or not words:
            break
        w = words.pop()
        if w in lookup:
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
    to_translate = []

    while 1:
        batch = get_n_uncached(words, wdict)
        if not batch:
            break
        bdict = dict(zip(batch, client.translate(batch, target_language=target_language)))
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
    lookup = translate(words)

    # with open('/Users/ak/projects/learnlang/%s.html' % ch_name, 'w') as fp:
    ttypes = '_'.join(target_types)
    with open('%s_%s_%s.html' % (ch_name, target_language, ttypes), 'w') as fp:
        fp.write('''<html>
        <head>
        <meta charset="UTF-8"/>
        </head>
        <body><style>
        .noun {color: hsl(120, 100%, 25%)}
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
                 ''')
        for n, par in enumerate(chapter):
            # par = par.replace(quote, "'")
            text = [[nltk.word_tokenize(w), ' '] for w in par.split()]
            text = [x for sl in text for x in sl]
            tups = [nltk.pos_tag(x) for x in text]
            tups = [x for sl in tups for x in sl]
            # print(tups[:5])

            out = []
            start = time()
            last1 = last2 = None
            for m, (w,tp) in enumerate(tups):
                if m>=2:
                    last2, last1 = tups[m-2][0], tups[m-1][0]
                if m==1 and tups[0][0] == start_quote:
                    pass
                # elif last1 and last2 and last1==quote and last2 in \
                #     ('I', 'don', 'can', 'isn', 'wouldn', 'you', 'haven', 'there', 'they', 'that', 'shouldn', 'it', 'didn'):
                #      pass
                # elif w[0]=="'" and len(w)>1:
                #     w = quote + w[1:]
                elif w=="n't":
                    pass
                elif w[-1] in string.ascii_letters:
                    pass
                    # out.append(' ')

                if tp in target_types and len(w)>1 and w[0] in string.ascii_letters:
                    tpl = '<span class="tooltip noun">{}<span class="tooltiptext">{}</span></span>'
                    if w in lookup:
                        out.append(tpl.format(lookup[w]['translatedText'], w))
                    else:
                        out.append(w)
                else:
                    out.append(w)
            fp.write('<p>' + ''.join(out).replace('&#39;', quote).replace('``', '"').replace("''", '"') + '</p>')
            print('{}/{}  {}'.format(n+1, len(chapter), int(time()-start)))
        fp.write('</body></html>')
    print('total {}'.format(int(time()-c_start)))
    data['cache'] = cache
    data.close()
    print("n_cached_trans", n_cached_trans)
    print('20 most common')
    for word, n in freq_table.most_common(20):
        print(n, '   ', word)

main(chapter)
