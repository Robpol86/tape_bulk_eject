import pytest

from tape_bulk_eject import AutoLoader, ExitDueToError


@pytest.mark.parametrize('host', ['.', 'fsefef', 'fake.local'])
def test_bad_host(caplog, host):
    autoloader = AutoLoader(host, 'user', 'pw')
    with pytest.raises(ExitDueToError):
        getattr(autoloader, '_query')('')
    log = caplog.records()[-1].message
    assert log.startswith('URL "http://{}/" is invalid: '.format(host))
    assert log.endswith('not known>')
