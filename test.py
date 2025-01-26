from core.api import FacebookCrawler

fb = FacebookCrawler('https://www.facebook.com/share/p/18WFDvV9nB/')
print(fb.getComments())