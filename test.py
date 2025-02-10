from core.api import *


url = 'https://www.facebook.com/61557603607953/videos/412237938114686/#'
proxy = 'hn01.quat.uk:8003:EagerProxy3:8fN1J7b6XB'
fb = FacebookCrawler(url=url, proxy=proxy)

print(fb.getComments())