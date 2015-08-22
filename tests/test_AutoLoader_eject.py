import StringIO

from tape_bulk_eject import AutoLoader


def test(monkeypatch):
    def urlopen(request):
        if request.get_full_url().endswith('commands.html'):
            html = """
                <center>
                    <img src="tape.gif" title="00007FA" onclick="from_to(slot15)" />
                    <img src="tape.gif" title="00008FA" onclick="from_to(slot16)" />
                    <img src="tape.gif" title="Empty" onclick="from_to(mailslot)" />
                </center>
            """
        else:
            html = """
                <center>
                    <img src="tape.gif" title="00007FA" onclick="from_to(slot15)" />
                    <img src="tape.gif" title="Empty" onclick="from_to(slot16)" />
                    <img src="tape.gif" title="00008FA" onclick="from_to(mailslot)" />
                </center>
            """
        return StringIO.StringIO(html)
    monkeypatch.setattr('urllib2.urlopen', urlopen)
    monkeypatch.setattr(AutoLoader, 'DELAY', 0.01)

    autoloader = AutoLoader('124t.local', '', '')
    autoloader.update_inventory()
    expected = {'00007FA': '15', '00008FA': '16'}
    assert autoloader.inventory == expected

    autoloader.eject('00008FA')
    expected = {'00007FA': '15', '00008FA': 'mailslot'}
    assert autoloader.inventory == expected
