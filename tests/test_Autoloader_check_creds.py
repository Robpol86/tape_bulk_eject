import StringIO
import urllib2

import pytest

from tape_bulk_eject import Autoloader, HandledError


def test(monkeypatch, caplog):
    def urlopen(handler):
        raise urllib2.HTTPError(handler.get_full_url(), 401, '', None, None)
    monkeypatch.setattr('urllib2.urlopen', urlopen)

    autoloader = Autoloader('124t.local', 'user', 'pw')
    with pytest.raises(HandledError):
        autoloader.check_creds()
    log = caplog.records()[-1].message
    assert log.endswith('Possibly rate limiting or invalid credentials.')

    def urlopen(_):
        return StringIO.StringIO('test67')
    monkeypatch.setattr('urllib2.urlopen', urlopen)
    autoloader.check_creds()
