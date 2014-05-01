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
import itertools
from argparse import ArgumentParser

# Default options
DEFAULT_PROXY_FILE = '/web/proxy.txt'
DEFAULT_MAX_DEPTH = 2
DEFAULT_THREAD_NUMBER = 1
DEFAULT_LANGUAGE = 'ru'

# Do not edit this options
GOOGLE_DOMAINS = open('data/google_domain.txt').read().splitlines()
GOOGLE_DOMAINS_ITER = itertools.cycle(GOOGLE_DOMAINS)
PROXY_FILE = '/web/proxy.txt'
BASE_SUGGEST_URL = 'http://%(hostname)s'\
                   '/complete/search?client=firefox&hl=%(lang)s&gl=%(lang)s&q=%(query)s'
DIGITS = '01234567890'
RU_CHARS = u'абвгдеёжзийклмнопрстуфхцчшщъыьэюя'
EN_CHARS = u'abcdefghijklmnopqrstuvwxyz'
USER_AGENT = 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/34.0.1847.132 Safari/537.36'

def build_query_url(query, lang='ru'):
    args = {
        'hostname': GOOGLE_DOMAINS_ITER.next(),
        'query': urllib.quote_plus(smart_str(query)),
        'lang': lang,
        #'hl': lang,
    }
    return BASE_SUGGEST_URL % args


def generate_extra_queries(query, depth, leading_space, trailing_space,
                           lang, int_modifiers, ext_modifiers):
    # Process trailing modifiers
    if query.endswith(' '):
        chars = ext_modifiers
    else:
        if depth == 1 and trailing_space:
            chars = ext_modifiers
        else:
            chars = int_modifiers

    chars += ' '

    for char in chars:
        if depth == 1 and trailing_space:
            char = u' %s' % char

        extended_query = u'%s%s' % (query, char)

        # Do not allow queries with more than one traling space
        if extended_query.endswith('  '):
            pass
        else:
            yield depth, extended_query

    # Process leading modifiers
    if query.startswith(' '):
        chars = ext_modifiers
    else:
        if depth == 1 and leading_space:
            chars = ext_modifiers
        else:
            chars = int_modifiers

    chars += ' '

    for char in chars:
        if depth == 1 and leading_space:
            char = u'%s ' % char

        extended_query = u'%s%s' % (char, query)

        # Do not allow queries with more than one traling space
        if extended_query.startswith('  '):
            pass
        else:
            yield depth, extended_query


def parse_response(body):
    keys = json.loads(body)[1]
    keys = [x.strip() for x in keys]
    return keys


def build_grab_for_query(query, lang=DEFAULT_LANGUAGE):
    g = Grab()
    g.setup(url=build_query_url(query, lang))
    g.setup(user_agent=USER_AGENT)
    g.setup(headers={'Accept-Language': 'ru'})
    return g


class SuggestSpider(Spider):
    def prepare(self):
        self.keys = set()

    def generate_task(self, query, depth):
        g = build_grab_for_query(query, self.meta['language'])
        return Task('result', grab=g, query=query, depth=depth)

    def task_generator(self):
        for line in open(self.meta['query_file']):
            query = line.strip().decode('utf-8')
            yield self.generate_task(query, depth=0)

    def task_result(self, grab, task):
        keys = parse_response(grab.response.body)
        valid_keys = []

        relevant_key_count = 0

        for key in keys:
            if not task.query in key:
                pass
            elif (task.depth == 0 and
                  self.meta['trailing_space'] and
                  not u'%s ' % task.query in key and
                  not key.endswith(task.query)
            ):
                pass
            elif (task.depth == 0 and
                  self.meta['leading_space'] and
                  not u' %s' % task.query in key and
                  not key.startswith(task.query)
            ):
                pass
            else:
                relevant_key_count += 1
                if not key in self.keys:
                    valid_keys.append(key)
                    self.keys.add(key)
        print u'%s, total: %d, valid: %d' % (task.query, len(keys), len(valid_keys))

        # DO NOT expand search if results belong to another query
        #
        # If any of results contains the search query
        if relevant_key_count:
            for key in valid_keys:
                yield self.generate_task(key, depth=0)

        # If not too depth
        if task.depth < self.meta['max_depth']:
            # If number of results is enough to expand search
            if len(keys) == 10:
                # DO NOT expand search if results belong to another query
                #
                # If any of results contains the search query
                if relevant_key_count:
                    for query_depth, query in generate_extra_queries(task.query,
                                                                     task.depth + 1,
                                                                     self.meta['leading_space'],
                                                                     self.meta['trailing_space'],
                                                                     self.meta['language'],
                                                                     self.meta['int_modifiers'],
                                                                     self.meta['ext_modifiers']):
                        yield self.generate_task(query, depth=query_depth)

    def shutdown(self):
        print 'Found keys: %s' % len(self.keys)
        with open('result.txt', 'w', 'utf-8') as out:
            data = '\n'.join(sorted(self.keys))
            out.write(data)


def main():
    logging.basicConfig(level=logging.DEBUG)
    logging.getLogger('grab.network').setLevel(logging.INFO)

    parser = ArgumentParser(description='Google Suggestion Scraper')
    parser.add_argument('query_file')
    parser.add_argument('-l', '--language', help='Language', default=DEFAULT_LANGUAGE)
    parser.add_argument('-t', '--thread-number', type=int, default=DEFAULT_THREAD_NUMBER)
    parser.add_argument('-p', '--proxy-file', type=str, default=DEFAULT_PROXY_FILE)
    parser.add_argument('-d', '--max-depth', type=int, default=DEFAULT_MAX_DEPTH)
    parser.add_argument('--leading-space', default='yes', choices=('yes', 'no'))
    parser.add_argument('--trailing-space', default='yes', choices=('yes', 'no'))
    args = parser.parse_args()

    if args.language == 'ru':
        int_modifiers = RU_CHARS + DIGITS
        ext_modifiers = RU_CHARS + EN_CHARS + DIGITS
    else:
        int_modifiers = EN_CHARS + DIGITS
        ext_modifiers = EN_CHARS + DIGITS

    bot = SuggestSpider(
        thread_number=args.thread_number,
        meta={
            'query_file': args.query_file,
            'language': args.language,
            'max_depth': args.max_depth,
            'leading_space': args.leading_space == 'yes',
            'trailing_space': args.trailing_space == 'yes',
            'int_modifiers': int_modifiers,
            'ext_modifiers': ext_modifiers,
        },
    )
    if args.proxy_file:
        bot.load_proxylist(args.proxy_file, 'text_file')
    try:
        bot.run()
    except KeyboardInterrupt:
        pass
    print bot.render_stats()


if __name__ == '__main__':
    main()
