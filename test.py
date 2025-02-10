from core.api import *


url = 'https://www.facebook.com/100063213220268/videos/2049324475432423/#'
proxy = 'hn01.quat.uk:8003:EagerProxy3:8fN1J7b6XB'
fb = FacebookCrawler(url=url, proxy=proxy)

print(fb.getComments())