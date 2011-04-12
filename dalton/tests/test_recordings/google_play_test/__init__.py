import os
import dalton
from dalton import FileWrapper

here = os.path.abspath(os.path.dirname(__file__))

class StepNumber0(object):
    recorded_request = {
        'headers':  {},
        'url': '/',
        'method': 'GET',
        'body': None,
    }
    recorded_response = {
        'headers':  [('x-xss-protection', '1; mode=block'),
                     ('transfer-encoding', 'chunked'),
                     (                    'set-cookie',
                                          'PREF=ID=3279d0929fca78d5:FF=0:TM=1302637588:LM=1302637588:S=i_kWrFgBrJtwEvEm; expires=Thu, 11-Apr-2013 19:46:28 GMT; path=/; domain=.google.com, NID=45=X7dXgbe4F6Jdn4udhrU5OtFjnxxI43eFW7izPE872KjTXTLdWDwqFbPo8gqTobyhdkmlS8eSvF1mM3df5DP9yBc-YLcJrGF8_NjYb4Jdy859JvvtPFh7yh4uFWJZc03G; expires=Wed, 12-Oct-2011 19:46:28 GMT; path=/; domain=.google.com; HttpOnly'),
                     ('expires', '-1'),
                     ('server', 'gws'),
                     ('cache-control', 'private, max-age=0'),
                     ('date', 'Tue, 12 Apr 2011 19:46:28 GMT'),
                     ('content-type', 'text/html; charset=ISO-8859-1')],
        'body': FileWrapper('step_0_response.txt', here),
        'status': 200,
        'reason': 'OK',
        'version': 11,
    }
    next_step = 'None'
    
    def handle_request(self, request):
        assert dalton.request_match(request, self.recorded_request)
        return (self.next_step, dalton.create_response(self.recorded_response))

