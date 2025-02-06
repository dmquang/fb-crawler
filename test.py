from core.api import *


url = 'https://www.facebook.com/61563722176087/videos/504913988966768/'
proxy = '14.189.51.35:36584:shopmanh516:proxymanh516'
fb = FacebookToken(token='EAAAAAYsX7TsBOwfDk3bic61426G8Ebep1FAAzPPVMEZCAjATa1tqLBkNmjY5O84pVmzAKspcJ7AwnjolYvQNVpJMhdRlEz11lauMjngZCWIZAwXR07ADaMeaZCW6CsQCksurt08IzBTeFYBk06FBZCJftHv7eZA1wLc2TZB7AKBWTagqZCExIG79x1AXo6ZAW68ZCROwZDZD', proxy=proxy)

print(fb.getComments())