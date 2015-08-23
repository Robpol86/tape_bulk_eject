import StringIO

from tape_bulk_eject import Autoloader, main


def test_nothing_to_do(monkeypatch, caplog):
    def urlopen(_):
        html = '<center><img src="" title="in_mailslot" onclick="from_to(mailslot)" /></center>'
        return StringIO.StringIO(html)
    monkeypatch.setattr('urllib2.urlopen', urlopen)
    monkeypatch.setattr(Autoloader, 'DELAY', 0.01)

    main({'tapes': ['not_in_autoloader', 'in_mailslot'], 'host': '', 'user': '', 'pass': ''})
    records = caplog.records()
    messages = [r.message for r in records]
    assert 'not_in_autoloader not in autoloader, skipping.' in messages
    assert 'in_mailslot already in mailslot, skipping.' in messages
    assert 'No tapes to eject. Nothing to do.' in messages
