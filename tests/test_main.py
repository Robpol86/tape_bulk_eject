import StringIO

import pytest

from tape_bulk_eject import ExitDueToError, main


def test_tape_not_found(monkeypatch, caplog):
    def urlopen(_):
        html = """
            <center>
                <img src="tape.gif" title="00007FA" onclick="from_to(slot15)" />
                <img src="tape.gif" title="00008FA" onclick="from_to(slot16)" />
                <img src="tape.gif" title="Empty" onclick="from_to(mailslot)" />
            </center>
        """
        return StringIO.StringIO(html)
    monkeypatch.setattr('urllib2.urlopen', urlopen)

    config = {'tapes': ['99999FA'], 'host': '', 'user': '', 'pass': ''}
    with pytest.raises(ExitDueToError):
        main(config)
    log = caplog.records()[-1].message
    assert log == 'Requested tape not found in autoloader: 99999FA'
