#!/usr/bin/env python
import nltk
import shelve, string
from time import time
import sys, itertools
from google.cloud import translate

target_language = 'es'
argv=sys.argv
del argv[0]
if '-fr' in argv:
    target_language = 'fr'
    argv.remove('-fr')

quote = '’'
start_quote = '‘'
c_start = time()

ch_name = argv[0]
chapter = open('%s.txt' % ch_name).read().split('\n\n')
client = translate.Client()
data = shelve.open('data')
cache = data.get('cache', {})
if target_language not in cache:
    cache[target_language] = {}
lookup = cache[target_language]
skip_words = ['ll']

n_cached = [0]

def make_trans_list(chapter):
    for n, par in enumerate(chapter):
        # par = par.replace(quote, "'")
        text = nltk.word_tokenize(par)
        tups = nltk.pos_tag(text)
        for w,tp in tups:
            if tp=='NN' and w[0] in string.ascii_letters and w not in skip_words:
                yield w

def get_n_uncached(words, wdict, n=128):
    lst = []
    while 1:
        if n<=0 or not words:
            break
        w = words.pop()
        if w in lookup:
            wdict[w] = lookup[w]
            n_cached[0] += 1
        else:
            lst.append(w)
            n-=1
    return lst

def translate(words):
    wdict = {}
    to_translate = []
    n_cached = 0

    while 1:
        batch = get_n_uncached(words, wdict)
        if not batch:
            break
        bdict = zip(batch, client.translate(batch, target_language=target_language))
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
    lookup = translate(words)

    # with open('/Users/ak/projects/learnlang/%s.html' % ch_name, 'w') as fp:
    with open('%s_%s.html' % (ch_name, target_language), 'w') as fp:
        fp.write('''<html><body><style>
        .noun {color: hsl(120, 100%, 25%)}
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
            print(tups[:5])

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

                if tp=='NN' and len(w)>1 and w[0] in string.ascii_letters:
                    tpl = '<span class="tooltip noun">{}<span class="tooltiptext">{}</span></span>'
                    if w in lookup:
                        out.append(tpl.format(lookup[w]['translatedText'], w))
                    else:
                        out.append(w)
                else:
                    out.append(w)
            fp.write('<p>' + ''.join(out).replace('&#39;', quote) + '</p>')
            print('{}/{}  {}'.format(n+1, len(chapter), int(time()-start)))
        fp.write('</body></html>')
    print('total {}'.format(int(time()-c_start)))
    data['cache'] = cache
    data.close()
    print("n_cached", n_cached)
main(chapter)
