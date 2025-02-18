from core.api import *


url = 'https://www.facebook.com/share/r/18GP8nq38w/'
proxy = '42.96.5.233:15949:tuanlee15949:aqofw'

fb = FacebookCrawler(url=url, proxy=proxy)

print(fb.getComments())
print(fb.getCount())

