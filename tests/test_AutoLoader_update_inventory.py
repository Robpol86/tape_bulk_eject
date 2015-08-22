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


def test_bad_attrs(monkeypatch, caplog):
    def urlopen(_):
        html = '<img src="ign" onclick="from_to(slot1)"><center><img src="" title="" onclick="x">'
        return StringIO.StringIO(html)
    monkeypatch.setattr('urllib2.urlopen', urlopen)

    autoloader = AutoLoader('host', '', '')
    with pytest.raises(ExitDueToError):
        autoloader.update_inventory()

    log = caplog.records()[-1].message
    assert log == 'Attribute "onclick" in img tag is invalid: x'


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
        '00001FA': '1',
        '00002FA': '2',
        '00003FA': '3',
        '00004FA': '4',
        '00005FA': '5',
        '00006FA': '6',
        '00007FA': '7',
        '00008FA': '8',
        '000016FA': '16',
        '000019FA': 'drive',
        '000018FA': 'picker',
        '000017FA': 'mailslot',
    }
    assert autoloader.inventory == expected

    def urlopen(_):
        html = """
            <center>
                <img src="tape.gif" title="00001FA" onclick="from_to(slot1)" />
                <img src="tape.gif" title="00002FA" onclick="from_to(slot2)" />
                <img src="tape.gif" title="00003FA" onclick="from_to(slot3)" />
                <img src="tape.gif" title="00004FA" onclick="from_to(slot4)" />
                <img src="tape.gif" title="00005FA" onclick="from_to(slot5)" />
                <img src="tape.gif" title="00006FA" onclick="from_to(slot6)" />
                <img src="tape.gif" title="00007FA" onclick="from_to(slot7)" />
                <img src="tape.gif" title="00008FA" onclick="from_to(slot8)" />
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
        '00001FA': '1',
        '00002FA': '2',
        '00003FA': '3',
        '00004FA': '4',
        '00005FA': '5',
        '00006FA': '6',
        '00007FA': '7',
        '00008FA': '8',
        '10016FA': '16',
    }
    assert autoloader.inventory == expected
