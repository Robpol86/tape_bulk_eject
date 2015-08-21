import StringIO

import pytest

from tape_bulk_eject import AutoLoader, ExitDueToError


@pytest.mark.parametrize('html', ['', '</html>', '<head></head><body>Test</body>'])
def test_bad_html(monkeypatch, caplog, html):
    def urlopen(_):
        return StringIO.StringIO(html)
    monkeypatch.setattr('urllib2.urlopen', urlopen)

    autoloader = AutoLoader('host', '', '')
    with pytest.raises(ExitDueToError):
        autoloader.update_inventory()

    log = caplog.records()[-1].message
    assert log == 'Invalid HTML, found no regex matches.'
