import StringIO
import urllib2

import pytest

from tape_bulk_eject import Autoloader


@pytest.mark.parametrize('error', ['Error while ejecting.', 'drive locked?', 'Tape did not move.'])
def test(monkeypatch, caplog, error):
    def urlopen(request):
        if not hasattr(urlopen, '___raised'):
            setattr(urlopen, '___raised', True)
            if error == 'Error while ejecting.':
                raise urllib2.HTTPError(request.get_full_url(), 401, '', None, None)
            elif error == 'drive locked?':
                html = '<center><img src="" title="00008FA" onclick="from_to(drive)" /></center>'
            else:
                html = '<center><img src="" title="00008FA" onclick="from_to(slot1)" /></center>'
        else:
            html = '<center><img src="" title="00008FA" onclick="from_to(mailslot)" /></center>'
        return StringIO.StringIO(html)
    monkeypatch.setattr('urllib2.urlopen', urlopen)
    monkeypatch.setattr(Autoloader, 'DELAY', 0.01)
    monkeypatch.setattr(Autoloader, 'DELAY_ERROR', 0.01)

    autoloader = Autoloader('124t.local', '', '')
    autoloader.inventory['00008FA'] = '16'  # Doesn't matter where it is here.
    autoloader.eject('00008FA')
    assert autoloader.inventory == {'00008FA': 'mailslot'}

    records = caplog.records()
    assert [r for r in records if error in r.message]
