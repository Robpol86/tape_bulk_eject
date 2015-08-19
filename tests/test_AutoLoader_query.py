import urllib2

import pytest

from tape_bulk_eject import AutoLoader, ExitDueToError


@pytest.mark.parametrize('host', ['.', 'fsefef', 'fake.local'])
def test_bad_host(caplog, host):
    autoloader = AutoLoader(host, 'user', 'pw')
    with pytest.raises(ExitDueToError):
        getattr(autoloader, '_query')('')
    log = caplog.records()[-1].message
    assert log.startswith('URL "http://{}/" is invalid: '.format(host))
    assert log.endswith('not known>')


@pytest.mark.parametrize('code', [404, 401])
def test_bad_host_creds(monkeypatch, caplog, code):
    def urlopen(_):
        raise urllib2.HTTPError('http://124t.local/page.html', code, '', None, None)
    monkeypatch.setattr('urllib2.urlopen', urlopen)

    autoloader = AutoLoader('124t.local', 'user', 'pw')
    with pytest.raises(ExitDueToError):
        getattr(autoloader, '_query')('page.html')
    log = caplog.records()[-1].message
    if code == 404:
        expected = '404 Not Found on: http://124t.local/page.html'
    else:
        expected = '401 Unauthorized (bad credentials?) on: http://124t.local/page.html'
    assert log == expected
