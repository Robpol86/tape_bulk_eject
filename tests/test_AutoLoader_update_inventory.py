import StringIO

import pytest

from tape_bulk_eject import AutoLoader, ExitDueToError


def test_bad_html(monkeypatch, caplog):
    def urlopen(_):
        return StringIO.StringIO('This is not HTML.')
    monkeypatch.setattr('urllib2.urlopen', urlopen)

    autoloader = AutoLoader('host', '', '')
    with pytest.raises(ExitDueToError):
        autoloader.update_inventory()

    log = caplog.records()[-1].message
    assert log == 'Invalid HTML, found no regex matches.'


@pytest.mark.parametrize('html,expected', [
    ('<center><img src="" title="" onclick="x">', 'Attribute "onclick" in img tag is invalid: x'),
    ('<center><img src="" title="" onclick="from_to(slot0)">', 'Unknown slot: 0'),
])
def test_bad_attrs(monkeypatch, caplog, html, expected):
    def urlopen(_):
        return StringIO.StringIO('<img src="ignore.me" onclick="from_to(slot1)">' + html)
    monkeypatch.setattr('urllib2.urlopen', urlopen)

    autoloader = AutoLoader('host', '', '')
    with pytest.raises(ExitDueToError):
        autoloader.update_inventory()

    log = caplog.records()[-1].message
    assert log == expected
