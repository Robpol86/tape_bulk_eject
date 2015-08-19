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


def test_bad_page(monkeypatch, caplog):
    def urlopen(_):
        raise urllib2.HTTPError('http://124t.local/dne.html', 404, "Can't find file", None, None)
    monkeypatch.setattr('urllib2.urlopen', urlopen)

    autoloader = AutoLoader('124t.local', 'user', 'pw')
    with pytest.raises(ExitDueToError):
        getattr(autoloader, '_query')('dne.html')
    log = caplog.records()[-1].message
    expected = (
        "URL \"http://124t.local/dne.html\" did not return HTTP 200: "
        "HTTP Error 404: Can't find file"
    )
    assert log == expected
