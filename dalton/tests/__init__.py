import os
import unittest
import dalton
import urllib
dalton.inject()

here = os.path.abspath(os.path.dirname(__file__))


class TestRecorder(unittest.TestCase):
    def _makeHttp(self, host):
        from httplib import HTTPConnection
        return HTTPConnection(host)
    
    def testRecord(self):
        h = self._makeHttp('www.google.com')
        recorder = dalton.Recorder(caller=h)
        with recorder.recording():
            h.request('GET', '/')
            resp = h.getresponse()
            body = resp.read()
        assert len(recorder._interaction) == 1
    
    def testSave(self):
        h = self._makeHttp('www.google.com')
        params = urllib.urlencode({'q': 'dalton'})
        recorder = dalton.Recorder(caller=h)
        with recorder.recording():
            h.request('GET', '/')
            resp = h.getresponse()
            body = resp.read()
            h.request('POST', '/', body=params)
            resp = h.getresponse()
            body = resp.read()
        test_dir = os.path.join(here, 'test_recordings', 'google_test')
        recorder.save(test_dir)
                
        assert len(recorder._interaction) == 2
        assert os.path.exists(test_dir)
        assert os.path.isdir(test_dir)
        assert os.path.exists(os.path.join(test_dir, '__init__.py'))
        assert os.path.exists(os.path.join(test_dir, 'step_1_request.txt'))


class TestGlobalRecorder(unittest.TestCase):
    def _makeHttp(self, host):
        from httplib import HTTPConnection
        return HTTPConnection(host)
    
    def testRecord(self):
        h = self._makeHttp('www.google.com')
        recorder = dalton.Recorder(caller=h)
        with recorder.recording():
            h.request('GET', '/')
            resp = h.getresponse()
            body = resp.read()
        assert len(recorder._interaction) == 1
    
    def testSave(self):
        h = self._makeHttp('www.google.com')
        params = urllib.urlencode({'q': 'dalton'})
        recorder = dalton.Recorder(use_global=True)
        with recorder.recording():
            h.request('GET', '/')
            resp = h.getresponse()
            body = resp.read()
            h.request('POST', '/', body=params)
            resp = h.getresponse()
            body = resp.read()
        test_dir = os.path.join(here, 'test_recordings', 'google_test')
        recorder.save(test_dir)
                
        assert len(recorder._interaction) == 2
        assert os.path.exists(test_dir)
        assert os.path.isdir(test_dir)
        assert os.path.exists(os.path.join(test_dir, '__init__.py'))
        assert os.path.exists(os.path.join(test_dir, 'step_1_request.txt'))


class TestPlayer(unittest.TestCase):
    def _makeHttp(self, host):
        from httplib import HTTPConnection
        return HTTPConnection(host)
    
    def testPlay(self):
        h = self._makeHttp('www.google.com')
        test_dir = os.path.join(here, 'test_recordings', 'google_play_test')
        player = dalton.Player(caller=h, playback_dir=test_dir)
        with player.playing():
            h.request('GET', '/')
            resp = h.getresponse()
            body = resp.read()
        # This shouldnt' do anything
        resp.close()
        
        assert '<title>GoogleFoo</title>' in body
        assert resp.getheader('x-xss-protection') == '1; mode=block'
        assert len(resp.getheaders()) == 8


class TestGlobalPlayer(unittest.TestCase):
    def _makeHttp(self, host):
        from httplib import HTTPConnection
        return HTTPConnection(host)
    
    def testPlay(self):
        h = self._makeHttp('www.google.com')
        test_dir = os.path.join(here, 'test_recordings', 'google_play_test')
        player = dalton.Player(playback_dir=test_dir, use_global=True)
        with player.playing():
            h.request('GET', '/')
            resp = h.getresponse()
            body = resp.read()
        # This shouldnt' do anything
        resp.close()
        
        assert '<title>GoogleFoo</title>' in body
        assert resp.getheader('x-xss-protection') == '1; mode=block'
        assert len(resp.getheaders()) == 8


class TestFileWrapper(unittest.TestCase):
    def testLoad(self):
        fw = dalton.FileWrapper('step_0_response.txt', 
            os.path.join(here, 'test_files'))
        content = fw.load()
        assert 'The document has moved' in content
        assert str(fw).startswith("FileWrapper('step_0_response.txt',")
    
    def testSave(self):
        fw = dalton.FileWrapper('test_output.txt', 
            os.path.join(here, 'test_files'))
        fw.write('some_content')
        content = fw.load()
        assert 'some_content' == content
