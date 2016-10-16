import sys

if __name__ == '__main__':
    try:
        from urllib.request import urlopen, URLError
    except ImportError:
        from urllib2 import urlopen, URLError

    url = sys.argv[1]
    headers = {'Content-Type': 'text/plain; charset=utf-8'}
    try:
        resp = urlopen(url)
        line = resp.readline().decode('ascii') # py3
    except URLError:
        line = 'failed to read %s' % url
    sys.stdout.write(line)
    sys.stdout.flush()
