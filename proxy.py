#!/usr/bin/python
import sys
import cgi
from optparse import OptionParser
from httplib import HTTPConnection

parser = OptionParser()
parser.add_option('-k', '--key', dest='key',
                  help='Github plugin private key')
parser.add_option('-t', '--trac', dest='host',
                  help='Trac host',
                  default='localhost')
parser.add_option('-u', '--url', dest='url',
                  default='/',
                  help='Trac base url')
parser.add_option('-p', '--port', dest='port',
                  help='Port where to listen',
                  default=8000)

options, args = parser.parse_args(sys.argv[1:])

def proxy(environ, start_response):
    if environ['REQUEST_METHOD'] == 'POST' and environ['PATH_INFO'].startswith('/' + options.key):
        form_data = environ['wsgi.input']
        data = cgi.FieldStorage(form_data, environ=environ, keep_blank_values=True)
        payload = data.getfirst('payload', '')
        
        try:
            conn = HTTPConnection(options.host)
            conn.request('POST', options.url + '/github/' + options.key,
                        body=payload,
                        headers={ 'Content-Type' : 'application/json' })
            conn.getresponse()
        except socket.error, e:
            start_response('500 Server Error', [('Content-Type', 'text/html')])
            return ['error']
    
        start_response('200 OK', [('Content-Type', 'text/html')])
        return ['ok']
    else:
        start_response('404 Not Found', [('Content-Type', 'text/html')])
        return ['not found']
        
if __name__ == '__main__':
    from paste import httpserver
    httpserver.serve(proxy, host='127.0.0.1', port=options.port)
