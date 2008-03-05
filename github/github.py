from trac.core import *
from trac.web import IRequestHandler
from hook import CommitHook
import json

GITHUB_KEY = '9953d62bbc3905491971513876218f39'

class GithubPlugin(Component):
    implements(IRequestHandler)
    
    def __init__(self):
        self.hook = CommitHook(self.env)
    
    # IRequestHandler methods
    def match_request(self, req):
        return req.path_info.rstrip('/') == ('/github/%s' % GITHUB_KEY) and req.method == 'POST'
    
    def process_request(self, req):
        try:
            data = json.read(req.read())

            for sha1, commit in data['commits'].items():
                self.hook.process(commit)
            req.send_response(200)
            req.send_header('Content-Type', 'text/plain')
            req.end_headers()
            req.write('Hello world!')
        except json.ReadException, e:
            req.send_response(400)
            req.send_header('Content-type', 'text/plain')
            req.end_headers()
            req.write(e.message)
