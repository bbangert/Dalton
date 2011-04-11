import httplib
import logging
import threading
import pprint
import os
import sys
import StringIO
from contextlib import contextmanager

log = logging.getLogger(__name__)

__all__ = ['inject', 'Recorder']


def inject():
    """Monkey-patch httplib with Dalton"""
    httplib.HTTPConnection._orig_request = httplib.HTTPConnection.request
    httplib.HTTPConnection._orig_getresponse = httplib.HTTPConnection.getresponse
    httplib.HTTPConnection.request = _request
    httplib.HTTPConnection.getresponse = _getresponse
    httplib.HTTPConnection._intercept = _intercept


class RegisteredInjections(threading.local):
    """Setup as a module-global to track injections that are
    registered"""
    def __init__(self):
        threading.local.__init__(self)
        self.callers = {}

_registered_injections = RegisteredInjections()


class FileWrapper(object):
    """A file-wrapper for easy load/save of body content"""
    def __init__(self, filename):
        self.filename = filename
    
    def write(self, content, directory):
        file_loc = os.path.join(directory, self.filename)
        with open(file_loc, 'w') as f:
            f.write(content)
    
    def load(self, directory):
        file_loc = os.path.join(directory, self.filename)
        with open(file_loc, 'r') as f:
            content = f.read()
        return content
    
    def __repr__(self):
        return "FileWrapper('%s')" % self.filename
    __str__ = __repr__


class InteractionStep(object):
    """Represents an interaction step used for recording and
    serializing interactions with an HTTP server"""
    def __init__(self, host=None):
        self.host = host
        self.request_method = self.request_url = self.request_body = None
        self.request_headers = {}
        self.response_status = self.response_reason = None
        self.response_headers = {}
        self.response_body = self.response_version = None
    
    def _pprint(self, obj):
        out = StringIO.StringIO()
        pprint.pprint(obj, indent=21, stream=out)
        out.seek(0)
        content = out.read()
        content = content[:1] + content[21:]
        return content.strip()
    
    def serialize(self, step_number, next_step, output_dir):
        """Save the request/response bodies to the output dir and
        return the class code for this step"""
        
        request_body = self.request_body
        if request_body:
            request_body = FileWrapper('step_%s_request.txt' % step_number)
            request_body.write(self.request_body, output_dir)
        response_body = self.response_body
        if response_body:
            response_body = FileWrapper('step_%s_response.txt' % step_number)
            response_body.write(self.response_body, output_dir)
        data = {
            'step_number': step_number,
            'request_url': self.request_url,
            'request_method': self.request_method,
            'request_body': request_body,
            'request_headers': self._pprint(self.request_headers),
            'response_headers': self._pprint(self.response_headers),
            'response_body': response_body,
            'response_status': self.response_status,
            'response_version': self.response_version,
            'response_reason': self.response_reason,
            'next_step': next_step
        }
        return step_template % data


class Recorder(object):
    def __init__(self, caller):
        self._caller = caller
        self._interaction = []
        self._current_step = None
    
    def start(self):
        """Called to begin/resume a recording of an interaction"""
        callers = _registered_injections.callers
        callers[self._caller] = {'mode': 'normal', 'recorder': self}
    
    def stop(self):
        """Called to stop recording an interaction"""
        if self._caller in _registered_injections.callers:
            del _registered_injections.callers[self._caller]
    
    @contextmanager
    def recording(self):
        try:
            self.start()
            yield
        finally:
            self.stop()
    
    def _record_request(self, host, method, url, body, headers):
        new_step = InteractionStep(host=host)
        new_step.request_method = method
        new_step.request_url = url
        new_step.request_body = body
        new_step.request_headers = headers
        self._current_step = new_step
    
    def _record_response(self, http_response):
        new_step = self._current_step
        if not new_step:
            raise Exception("Called record response when no request was made.")
        
        new_step.response_status = http_response.status
        new_step.response_reason = http_response.reason
        new_step.response_version = http_response.version
        new_step.response_headers = http_response.getheaders()
        body = http_response.read()
        new_step.response_body = body
        http_response.fp = StringIO.StringIO(body)
        http_response.length = len(body)
        self._interaction.append(new_step)
        self._current_step = None
    
    def save(self, output_dir):
        if os.path.exists(output_dir) and not os.path.isdir(output_dir):
            raise Exception("Name already exists, and is not a directory.")
        
        if not os.path.exists(output_dir):
            os.mkdir(output_dir)
        
        module_str = ['import dalton', 'from dalton import FileWrapper', '']
        step_len = len(self._interaction)
        for step_number, step in enumerate(self._interaction):
            if step_number + 1 < step_len:
                next_step = 'StepNumber%s' % (step_number + 1)
            else:
                next_step = None
            module_str.append(step.serialize(step_number, next_step, output_dir))
            module_str.append('')
        
        init = os.path.join(output_dir, '__init__.py')
        with open(init, 'w') as f:
            f.write('\n'.join(module_str))
        return True


## HTTPConnection monkey-patch methods

def _request(self, method, url, body=None, headers=None):
    """Monkey-patched replacement request method"""
    headers = headers or {}
    intercept = self._intercept()
    if 'recorder' in intercept:
        intercept['recorder']._record_request(self.host, method, url, 
                                              body, headers)

    if intercept['mode'] == 'normal':
        return self._orig_request(method, url, body, headers)
    else:
        return intercept['playback'].request(method, url, body, headers)


def _getresponse(self):
    """Monkey-patched replacement getresponse method"""
    intercept = self._intercept()
    if intercept['mode'] == 'normal':
        response = self._orig_getresponse()
        if 'recorder' in intercept:
            intercept['recorder']._record_response(response)
        return response
    else:
        return intercept['playback'].getresponse()


def _intercept(self):
    """Monkey-patch intercept to determine call-stack location"""
    i_vars = _registered_injections.callers
    if not i_vars:
        return {'mode': 'normal'}
    
    try:
        raise Exception("Intentional to capture stack")
    except:
        pass
    tb = sys.exc_info()[2]
    stack = []
    while tb:
        stack.append(tb.tb_frame)
        tb = tb.tb_next
    
    for frame in stack[::-1]:
        # Look up the stack for a variable indicating we should
        # get involved
        if 'self' not in frame.f_locals:
            continue
            
        frame_self = frame.f_locals['self']
        for key in i_vars:
            if frame_self.__class__ == key or frame_self == key:
                return i_vars[key]
    return {'mode': 'normal'}


## String templates used for Python module generation

step_template = """\
class StepNumber%(step_number)s(object):
    recorded_request = {
        'headers':  %(request_headers)s,
        'url': '%(request_url)s',
        'method': '%(request_method)s',
        'body': %(request_body)s,
    }
    recorded_response = {
        'headers':  %(response_headers)s,
        'body': %(response_body)s,
        'status': %(response_status)s,
        'reason': '%(response_reason)s',
        'version': '%(response_version)s',
    }
    next_step = %(next_step)s
    
    def handle_request(self, request):
        assert dalton.request_match(request, self.recorded_request)
        return (self.next_step, dalton.create_response(self.recorded_response))
"""
