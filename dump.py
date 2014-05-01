#!/usr/bin/env python
import sys
from sug import build_grab_for_query, parse_response

def main():
    query = sys.argv[1]
    g = build_grab_for_query(query)
    g.request()
    for key in parse_response(g.response.body):
        print key


if __name__ == '__main__':
    main()
