import urllib2

import pytest

from tape_bulk_eject import AutoLoader, ExitDueToError


@pytest.mark.parametrize('host', ['.', 'i_do_not_exist'])
def test_bad_host(caplog, host):
    autoloader = AutoLoader(host, 'user', 'pw')
    request = urllib2.Request(autoloader.url)
    with pytest.raises(ExitDueToError):
        getattr(autoloader, '_query')(request)
    log = caplog.records()[-1].message
    assert log.startswith('URL "http://{}/" is invalid: '.format(host))
    assert log.endswith('not known>')


@pytest.mark.parametrize('code', [404, 401, 500])
def test_bad_host_creds(monkeypatch, caplog, code):
    def urlopen(handler):
        raise urllib2.HTTPError(handler.get_full_url(), code, '', None, None)
    monkeypatch.setattr('urllib2.urlopen', urlopen)

    autoloader = AutoLoader('124t.local', 'user', 'pw')
    request = urllib2.Request(autoloader.url)
    with pytest.raises(ExitDueToError):
        getattr(autoloader, '_query')(request)
    log = caplog.records()[-1].message
    if code == 404:
        expected = '404 Not Found on: http://124t.local/'
    elif code == 401:
        expected = '401 Unauthorized (bad credentials?) on: http://124t.local/'
    else:
        expected = 'http://124t.local/ returned HTTP {} instead of 200.'.format(code)
    assert log == expected
