# coding: utf-8
from grab import Grab
import urllib
import json
from sug import GOOGLE_DOMAINS

sample = '["колбаса а",["колбаса алан","колбаса аброй","колбаса армавирская","колбаса английский","колбаса атяшево","колбаса ала тоо","колбаса акниет","колбаса ансар","колбаса альпийская","колбаса абсолют"]]'

query = urllib.quote_plus('колбаса а')

for domain in open('data/google_domain.txt').read().splitlines():
    print 'Domain: %s' % domain
    g = Grab()
    url = 'http://%s/complete/search?client=firefox&hl=ru&gl=ru&q=%s' % (domain, query)
    g.go(url)
    print 'OK: %s' % (sample == g.response.body)
    if sample != g.response.body:
        import pdb; pdb.set_trace()
