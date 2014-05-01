#!/usr/bin/env python
# coding: utf-8
import sys
import string
import logging
from grab import Grab
from grab.spider import Spider, Task
from grab.tools.http import urlencode
from grab.tools.encoding import smart_str
import urllib
import json
from codecs import open

PROXY_FILE = '/web/proxy.txt'
BASE_SUGGEST_URL = 'https://clients1.google.com/complete'\
                   '/search?client=firefox&hl=%(lang)s&gl=%(lang)s&q=%(query)s'
DIGITS = '01234567890'
RU_LETTERS = u'абвгдеёжзийклмнопрстуфхцчшщъыьэюя'
EN_LETTERS = u'abcdefghijklmnopqrstuvwxyz'
MAX_DEPTH = 1
USER_AGENT = 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/34.0.1847.132 Safari/537.36'


def build_query_url(query, lang='ru'):
    args = {
        'query': urllib.quote_plus(smart_str(query)),
        'lang': lang,
        #'hl': lang,
    }
    return BASE_SUGGEST_URL % args


#def generate_queries(query):
    #chars = DIGITS + EN_LETTERS + RU_LETTERS
    #for char1 in chars:
        #for char2 in chars:
            #yield '%s %s%s' % (query, char1, char2)


def generate_extra_queries(query):
    chars = RU_LETTERS
    chars += ' '
    for char in chars:
        extended_query = u'%s%s' % (query, char)
        # Do not allow queries with more than one traling space
        if extended_query.endswith('  '):
            pass
        else:
            yield extended_query


def parse_response(body):
    keys = json.loads(body)[1]
    keys = [x.strip() for x in keys]
    return keys


def build_grab_for_query(query):
    g = Grab()
    g.setup(url=build_query_url(query))
    g.setup(user_agent=USER_AGENT)
    g.setup(headers={'Accept-Language': 'ru'})
    return g


class SuggestSpider(Spider):
    def prepare(self):
        self.keys = set()

    def generate_task(self, query, depth):
        g = build_grab_for_query(query)
        return Task('result', grab=g, query=query, depth=depth)

    def task_generator(self):
        for line in open(self.meta['query_file']):
            query = line.strip().decode('utf-8')
            yield self.generate_task(query, depth=0)

    def task_result(self, grab, task):
        keys = parse_response(grab.response.body)
        valid_keys = []
        for key in keys:
            #print 'KEY:', key
            if not task.query in key:
                pass
            else:
                if not key in self.keys:
                    valid_keys.append(key)
                    self.keys.add(key)
        print u'%s, total: %d, valid: %d' % (task.query, len(keys), len(valid_keys))

        for key in valid_keys:
            yield self.generate_task(key, depth=0)

        if task.depth < MAX_DEPTH:
            if len(keys) == 10:
                for query in generate_extra_queries(task.query):
                    yield self.generate_task(query, depth=task.depth + 1)

    def shutdown(self):
        print 'Found keys: %s' % len(self.keys)
        with open('result.txt', 'w', 'utf-8') as out:
            data = '\n'.join(self.keys)
            out.write(data)


def main():
    logging.basicConfig(level=logging.DEBUG)
    logging.getLogger('grab.network').setLevel(logging.INFO)
    query_file = sys.argv[1]
    bot = SuggestSpider(
        thread_number=10,
        meta={'query_file': query_file},
    )
    bot.load_proxylist(PROXY_FILE, 'text_file')
    try:
        bot.run()
    except KeyboardInterrupt:
        pass
    print bot.render_stats()


if __name__ == '__main__':
    main()
