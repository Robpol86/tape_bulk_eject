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
    expected = {
        '1': '', '2': '', '3': '', '4': '', '5': '', '6': '', '7': '', '8': '',
        '9': '', '10': '', '11': '', '12': '', '13': '', '14': '',
        '15': '00007FA',
        '16': '00008FA',
        'drive': '', 'picker': '', 'mailslot': '',
    }
    assert autoloader.inventory == expected

    autoloader.eject('00008FA')
    expected = {
        '1': '', '2': '', '3': '', '4': '', '5': '', '6': '', '7': '', '8': '',
        '9': '', '10': '', '11': '', '12': '', '13': '', '14': '',
        '15': '00007FA',
        '16': '',
        'drive': '', 'picker': '', 'mailslot': '00008FA',
    }
    assert autoloader.inventory == expected
