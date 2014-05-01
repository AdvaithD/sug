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

#BASE_SUGGEST_URL = 'http://clients5.google.com/complete/search?'
BASE_SUGGEST_URL = 'http://www.google.ru/s?q=%(query)s&sclient=psy-ab&tch=1'
DIGITS = '01234567890'
RU_LETTERS = u'абвгдеёжзийклмнопрстуфхцчшщъыьэюя'
EN_LETTERS = u'abcdefghijklmnopqrstuvwxyz'
USER_AGENT = 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/34.0.1847.132 Safari/537.36'


def build_query_url(query):
    args = {
        'query': urllib.quote_plus(smart_str(query)),
        #'hl': lang,
    }
    return BASE_SUGGEST_URL % args


def generate_queries(query):
    chars = DIGITS + EN_LETTERS + RU_LETTERS
    for char1 in chars:
        for char2 in chars:
            yield '%s %s%s' % (query, char1, char2)


def generate_extra_queries(query):
    chars = DIGITS + EN_LETTERS + RU_LETTERS
    if not query.endswith(' '):
        chars += ' '
    for char in chars:
        yield '%s%s' % (query, char)


def parse_response(body):
    body_fixed = body.replace('/*""*/', '')
    res = json.loads(body_fixed )
    suggest_res = json.loads(res['d'])
    keys = []
    for item in suggest_res[1]:
        val = item[0].replace('<b>', '').replace('</b>', '')
        keys.append(val)
    return keys


def build_grab_for_query(query):
    g = Grab()
    g.setup(url=build_query_url(query))
    g.setup(user_agent=USER_AGENT)
    g.setup(headers={'Accept-Language': 'ru'})
    return g


class SuggestSpider(Spider):
    def prepare(self):
        self.out = open('result.txt', 'w')
        self.keys = set()

    def generate_task(self, query):
        g = build_grab_for_query(query)
        return Task('result', grab=g, query=query)

    def task_generator(self):
        for line in open(self.meta['query_file']):
            query = line.strip().decode('utf-8')
            yield self.generate_task(query)

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
        if valid_keys:
            data = '\n'.join(valid_keys)
            self.out.write(data.encode('utf-8') + '\n')
        print u'%s, total: %d, valid: %d' % (task.query, len(keys), len(valid_keys))

        for key in valid_keys:
            yield self.generate_task(key)

            #for extra_query in generate_extra_queries(query):
                #yield Task('result', build_url(extra_query))


def main():
    logging.basicConfig(level=logging.DEBUG)
    logging.getLogger('grab.network').setLevel(logging.INFO)
    query_file = sys.argv[1]
    bot = SuggestSpider(
        thread_number=10,
        meta={'query_file': query_file},
    )
    bot.load_proxylist('/web/proxy.txt', 'text_file')
    try:
        bot.run()
    except KeyboardInterrupt:
        pass
    print bot.render_stats()


if __name__ == '__main__':
    main()
