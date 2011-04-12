======
Dalton
======

"I want you to be nice until it's time to not be nice."
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
    
    # save the response record
    recorder.save('google')

A folder called ``google`` will be created in the current directory for use
with dalton's playback facility.