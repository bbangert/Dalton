======
Dalton
======

"I want you to be nice, until it's time to not be nice."
    -- Dalton, Road-House

An httplib injection library for recording and playing back HTTP interactions.

Dalton monkey-patches two methods of httplib's HTTPConnection class to
intercept request/response interactions, and can play them back based on a
Dalton recording. To ease testing, the recording is generated Python code to
ease in customization of the response and to allow for branches in the
playback path.

Monkey-patched methods of HTTPConnection:
    - request
    - getresponse

Using the more verbose method to send/recieve requests with HTTPConnection is
not supported at this time.

**Note:** This is a first and early release, mainly so that I could use it
with mechanize to record/playback interactions. As mechanize only uses the
request/getresponse API on HTTPConnection, I have no interest in adding
intercept to the rest. Please feel free to fork this to add additional
features as I don't plan on adding them myself (though I will happily pull bug
fixes and feature additions with unit tests).

**Warning:** Dalton uses ``inspect.currentframe`` magic to derive the caller
which may only work on CPython (PyPy and Jython is untested).


Example
=======

Since dalton monkey-patches httplib, no modification is necessary of libraries
that utilize the supported methods.

::

    import dalton
    dalton.inject() # monkey-patch httplib
    
    from httplib import HTTPConnection
    h = HTTPConnection('www.google.com')
    
    # when recording, httplib capture is restricted by caller
    recorder = dalton.Recorder(caller=h)
    
    # record httplib calls in this block
    with recorder.recording():
        h.request('GET', '/')
        resp = h.getresponse()
        body = resp.read()
    
    # save the interaction
    recorder.save('google')

A folder called ``google`` will be created in the current directory for use
with dalton's playback facility.

Playing it back::
    
    import dalton
    dalton.inject() # monkey-patch httplib
    
    from httplib import HTTPConnection
    h = HTTPConnection('www.google.com')
    
    # load the player
    player = dalton.Player(caller=h, playback_dir='google')
    
    # run httplib calls against the player
    with player.playing():
        h.request('GET', '/')
        resp = h.getresponse()
        body = resp.read()
    
    # body is now the same as it was recorded, no calls to www.google.com
    # were made

This generates a directory ``google`` with the following layout:
    - ``__init__.py``
    - ``step_0_response.txt``

The contents of ``__init__.py`` contain the following generated playback
information::
    
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
                                              'PREF=ID=ff; expires=Thu, 11-Apr-2013 20:19:35 GMT; path=/; domain=.google.com, NID=45=fU; expires=Wed, 12-Oct-2011 20:19:35 GMT; path=/; domain=.google.com; HttpOnly'),
                         ('expires', '-1'),
                         ('server', 'gws'),
                         ('cache-control', 'private, max-age=0'),
                         ('date', 'Tue, 12 Apr 2011 20:19:35 GMT'),
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

This file can be modified after recordings to customize the playback, add
additional branches, etc.

Support
=======

Dalton is considered feature-complete as the project owner (Ben Bangert) has
no additional functionality or development beyond bug fixes planned. Bugs can
be filed on github, should be accompanied by a test case to retain current
code coverage, and should be in a Pull request when ready to be accepted into
the Dalton code-base.
