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


def test_tape_in_mailslot(monkeypatch, caplog):
    html = list()
    html.append("""<center><!-- First update_inventory() after check_creds() in main(). -->
        <img src="" title="tape1" onclick="from_to(slot1)" />
        <img src="" title="tape2" onclick="from_to(slot2)" />
    </center>""")
    html.append("""<center><!-- First eject() in main() loop. -->
        <img src="" title="tape1" onclick="from_to(mailslot)" />
        <img src="" title="tape2" onclick="from_to(slot2)" />
    </center>""")
    html.append("""<center><!-- update_inventory() in main() loop. -->
        <img src="" title="tape2" onclick="from_to(slot2)" />
    </center>""")
    html.append("""<center><!-- Second eject() in main() loop. -->
        <img src="" title="tape2" onclick="from_to(mailslot)" />
    </center>""")

    def urlopen(request):
        if request.get_full_url().endswith('config_ops.html'):
            return StringIO.StringIO('yes')
        return StringIO.StringIO(html.pop(0))
    monkeypatch.setattr('urllib2.urlopen', urlopen)
    monkeypatch.setattr(Autoloader, 'DELAY', 0.01)
    monkeypatch.setattr(Autoloader, 'DELAY_ERROR', 0.01)

    main({'tapes': ['tape1', 'tape2'], 'host': '', 'user': '', 'pass': ''})
    records = caplog.records()
    messages = [r.message for r in records]

    assert not html
    assert 'Tape in mailslot, remove to continue...' in messages
    assert 'Ejected 2 tapes.' in messages
