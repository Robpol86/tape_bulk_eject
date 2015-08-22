import StringIO
import time
import urllib2

import pytest

from tape_bulk_eject import Autoloader, HandledError


@pytest.mark.parametrize('host', ['.', 'i_do_not_exist'])
def test_bad_host(caplog, host):
    autoloader = Autoloader(host, 'user', 'pw')
    request = urllib2.Request(autoloader.url)
    with pytest.raises(HandledError):
        getattr(autoloader, '_query')(request)
    log = caplog.records()[-1].message
    assert log.startswith('URL "http://{}/" is invalid: '.format(host))
    assert log.endswith('not known>')


@pytest.mark.parametrize('code', [404, 500])
def test_http_errors(monkeypatch, caplog, code):
    def urlopen(handler):
        raise urllib2.HTTPError(handler.get_full_url(), code, '', None, None)
    monkeypatch.setattr('urllib2.urlopen', urlopen)

    autoloader = Autoloader('124t.local', 'user', 'pw')
    request = urllib2.Request(autoloader.url)
    with pytest.raises(HandledError):
        getattr(autoloader, '_query')(request)
    log = caplog.records()[-1].message
    if code == 404:
        expected = '404 Not Found on: http://124t.local/'
    else:
        expected = 'http://124t.local/ returned HTTP {} instead of 200.'.format(code)
    assert log == expected


def test_rate_limiting(monkeypatch):
    def urlopen(_):
        return StringIO.StringIO('test67')
    monkeypatch.setattr('urllib2.urlopen', urlopen)

    autoloader = Autoloader('124t.local', 'user', 'pw')
    request = urllib2.Request(autoloader.url)
    start_time = time.time()
    monkeypatch.setattr(Autoloader, 'DELAY', 1)

    assert getattr(autoloader, '_query')(request) == 'test67'
    assert time.time() - start_time < 0.1
    assert getattr(autoloader, '_query')(request) == 'test67'
    assert time.time() - start_time > 0.9
