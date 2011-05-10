import httplib
import inspect
import logging
import threading
import pprint
import os
import sys
import StringIO
from contextlib import contextmanager

log = logging.getLogger(__name__)

__all__ = ['inject', 'Recorder', 'Player', 'FileWrapper']


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
        self._global = False

_registered_injections = RegisteredInjections()


class FileWrapper(object):
    """A file-wrapper for easy load/save of body content"""
    def __init__(self, filename, directory):
        self.filename = filename
        self.directory = directory
    
    def write(self, content):
        file_loc = os.path.join(self.directory, self.filename)
        with open(file_loc, 'w') as f:
            f.write(content)
    
    def load(self):
        file_loc = os.path.join(self.directory, self.filename)
        with open(file_loc, 'r') as f:
            content = f.read()
        return content
    
    def __repr__(self):
        return "FileWrapper('%s', here)" % self.filename
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
            request_body = FileWrapper('step_%s_request.txt' % step_number, output_dir)
            request_body.write(self.request_body)
        response_body = self.response_body
        if response_body:
            response_body = FileWrapper('step_%s_response.txt' % step_number, output_dir)
            response_body.write(self.response_body)
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


class Request(object):
    pass


class Recorder(object):
    """Creates a recorder

    A Recorder instance records all httplib remote calls that originate
    under the ``caller`` provided during initialization while the
    recorder is active (has been started).

    """
    def __init__(self, caller=None, use_global=False):
        """Create a record for the given caller"""
        self._caller = caller
        self._global = use_global
        self._interaction = []
        self._current_step = None

    def start(self):
        """Called to begin/resume a recording of an interaction"""
        callers = _registered_injections.callers
        if self._global:
            callers['_global'] = {'mode': 'normal', 'recorder': self}
        else:
            callers[self._caller] = {'mode': 'normal', 'recorder': self}
        self._orig_global = _registered_injections._global
        _registered_injections._global = self._global

    def stop(self):
        """Called to stop recording an interaction"""
        if self._global and '_global' in _registered_injections.callers:
            del _registered_injections.callers['_global']
        elif self._caller in _registered_injections.callers:
            del _registered_injections.callers[self._caller]
        _registered_injections._global = self._orig_global

    @contextmanager
    def recording(self):
        """Content manager version of start/stop"""
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
        """Save the recorded http interaction session to the output
        directory"""
        if os.path.exists(output_dir) and not os.path.isdir(output_dir):
            raise Exception("Name already exists, and is not a directory.")

        if not os.path.exists(output_dir):
            os.mkdir(output_dir)

        module_str = [
            'import os', 'import dalton', 'from dalton import FileWrapper', '',
            'here = os.path.abspath(os.path.dirname(__file__))', ''
        ]
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


class Player(object):
    """HTTP Interaction Player

    Plays back an interaction from a dalton recording.

    """
    def __init__(self, playback_dir, caller=None, use_global=False):
        """Create a player from the playback_dir"""
        mod_name = playback_dir.split(os.path.sep)[-1]
        container_dir = playback_dir.split(os.path.sep)[:-1]
        sys.path.insert(0, os.path.sep.join(container_dir))
        self._caller = caller
        self._global = use_global
        self._module = __import__(mod_name)
        self._current_step = getattr(self._module, 'StepNumber0')
        self._current_request = None

    def play(self):
        callers = _registered_injections.callers
        if self._global:
            callers['_global'] = {'mode': 'playback', 'playback': self}
        else:
            callers[self._caller] = {'mode': 'playback', 'playback': self}
        self._orig_global = _registered_injections._global
        _registered_injections._global = self._global

    def stop(self):
        if self._global and '_global' in _registered_injections.callers:
            del _registered_injections.callers['_global']
        elif self._caller in _registered_injections.callers:
            del _registered_injections.callers[self._caller]
        _registered_injections._global = self._orig_global

    @contextmanager
    def playing(self):
        """Content manager version of start/stop"""
        try:
            self.play()
            yield
        finally:
            self.stop()

    def request(self, method, url, body=None, headers=None):
        if not self._current_step:
            raise Exception("Playback can't handle more requests, this is "
                            "the end of the chain.")
        req = Request()
        req.method = method
        req.url = url
        req.body = body
        req.headers = headers
        self._current_request = req

    def getresponse(self):
        if not self._current_step:
            raise Exception("Failed to find a step when a request was made.")
        
        if not self._current_request:
            raise Exception("getresponse called during playback before "
                            "a request was made.")

        step = self._current_step()
        next_step, response = step.handle_request(self._current_request)
        if next_step == 'None':
            self._current_step = None
        else:
            self._current_step = getattr(self._module, next_step)
        return response


## Used by generated Python modules

class DaltonHTTPResponse(object):
    def __init__(self, response=None):
        self._content = None
        self._headers = {}
        self.msg = httplib.HTTPMessage(StringIO.StringIO(), 0)
        if response:
            headers = response['headers']
            for header, value in headers:
                self.msg[header] = value
            self.msg.fp = None
            self.status = response['status']
            self.version = response['version']
            self.reason = response['reason']
            body = response['body']
            if isinstance(body, FileWrapper):
                body = body.load()
            self._content = StringIO.StringIO(body)

    def read(self, amt=None):
        if self._content is None:
            raise httplib.ResponseNotReady()
        return self._content.read(amt)

    def getheader(self, name, default=None):
        if self.msg is None:
            raise httplib.ResponseNotReady()
        return self.msg.getheader(name, default)

    def getheaders(self):
        if self.msg is None:
            raise httplib.ResponseNotReady()
        return self.msg.items()

    def close(self):
        pass


def request_match(request, recorded_request_dict):
    assert request.method == recorded_request_dict['method']
    assert request.url == recorded_request_dict['url']
    return True


def create_response(response_dict):
    return DaltonHTTPResponse(response_dict)


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
            
            # Ensure chunked is not set, since the StringIO replacement
            # goofs it up
            response.chunked = 0
        return response
    else:
        return intercept['playback'].getresponse()


def _intercept(self):
    """Monkey-patch intercept to determine call-stack location"""
    i_vars = _registered_injections.callers
    if not i_vars:
        return {'mode': 'normal'}
    if _registered_injections._global:
        return _registered_injections.callers['_global']
    
    result = None
    
    cur_frame = inspect.currentframe()
    stack = inspect.getouterframes(cur_frame)
    for frame_record in stack:
        frame = frame_record[0]
        
        # Look up the stack for a variable indicating we should
        # get involved
        if 'self' not in frame.f_locals:
            continue
            
        frame_self = frame.f_locals['self']
        for key in i_vars:
            if frame_self.__class__ == key or frame_self == key:
                result = i_vars[key]
                break

    # Cycles can be problematic depending on Python GC mode, explicitly
    # remove the frame references
    del cur_frame
    while stack:
        frame_record = stack.pop()
        del frame_record
    if result:
        return result
    else:
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
        'version': %(response_version)s,
    }
    next_step = '%(next_step)s'
    
    def handle_request(self, request):
        assert dalton.request_match(request, self.recorded_request)
        return (self.next_step, dalton.create_response(self.recorded_response))
"""
