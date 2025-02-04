from core.api import FacebookCrawler

fb = FacebookCrawler(url = 'https://www.facebook.com/share/v/186k9dYgVY/', proxy='14.189.51.35:36584:shopmanh516:proxymanh516')
print( fb.reaction_count, fb.comment_count)
print(fb.getComments())
