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


def test_valid(monkeypatch):
    def urlopen(_):
        html = """
            <img src="ignore.me" title="ignore" onclick="from_to(slot1)" />
            <center>
                <img src="ignore_me.too" onclick="from_to(slot1)" />
                <img src="tape.gif" title="00001FA" onclick="from_to(slot1)" />
                <img src="tape.gif" title="00002FA" onclick="from_to(slot2)" />
                <img src="tape.gif" title="00003FA" onclick="from_to(slot3)" />
                <img src="tape.gif" title="00004FA" onclick="from_to(slot4)" />
                <img src="tape.gif" title="00005FA" onclick="from_to(slot5)" />
                <img src="tape.gif" title="00006FA" onclick="from_to(slot6)" />
                <img src="tape.gif" title="00007FA" onclick="from_to(slot7)" />
                <img src="tape.gif" title="00008FA" onclick="from_to(slot8)" />
                <img src="tape.gif" title="000016FA" onclick="from_to(slot16)" />
                <img src="tape.gif" title="000017FA" onclick="from_to(mailslot)" />
                <img src="tape.gif" title="000018FA" onclick="from_to(picker)" />
                <img src="tape.gif" title="000019FA" onclick="from_to(drive)" />
            </center>
        """
        return StringIO.StringIO(html)
    monkeypatch.setattr('urllib2.urlopen', urlopen)
    monkeypatch.setattr(AutoLoader, 'DELAY', 0.01)
    autoloader = AutoLoader('host', '', '')
    autoloader.update_inventory()
    expected = {
        '1': '00001FA',
        '2': '00002FA',
        '3': '00003FA',
        '4': '00004FA',
        '5': '00005FA',
        '6': '00006FA',
        '7': '00007FA',
        '8': '00008FA',
        '9': '', '10': '', '11': '', '12': '', '13': '', '14': '', '15': '',
        '16': '000016FA',
        'drive': '000019FA',
        'picker': '000018FA',
        'mailslot': '000017FA',
    }
    assert autoloader.inventory == expected

    def urlopen(_):
        html = """
            <center>
                <img src="tape.gif" title="10016FA" onclick="from_to(slot16)" />
                <img src="tape.gif" title="Empty" onclick="from_to(mailslot)" />
                <img src="tape.gif" title="Empty" onclick="from_to(picker)" />
                <img src="tape.gif" title="Empty" onclick="from_to(drive)" />
            </center>
        """
        return StringIO.StringIO(html)
    monkeypatch.setattr('urllib2.urlopen', urlopen)
    autoloader.update_inventory()
    expected = {
        '1': '00001FA',
        '2': '00002FA',
        '3': '00003FA',
        '4': '00004FA',
        '5': '00005FA',
        '6': '00006FA',
        '7': '00007FA',
        '8': '00008FA',
        '9': '', '10': '', '11': '', '12': '', '13': '', '14': '', '15': '',
        '16': '10016FA',
        'drive': '',
        'picker': '',
        'mailslot': '',
    }
    assert autoloader.inventory == expected
