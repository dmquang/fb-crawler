from core.api import *


url = 'https://www.facebook.com/ButEDMMusique/posts/pfbid02oKDCVpz5iwX59NraqN7acoSSaphAtRwmB3RoNwgKvxkCL5NABVbrzcJqiQv5BEDKl'
proxy = '103.241.199.83:49335:proxymart49335:rYyiyrmD'

fb = FacebookCrawler(url=url, proxy=proxy)

print(fb.getComments())
print(fb.getCount())

