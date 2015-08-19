import pytest

from tape_bulk_eject import AutoLoader, ExitDueToError


@pytest.mark.parametrize('host', ['.', 'fsefef', 'fake.local'])
def test_bad_host(caplog, host):
    autoloader = AutoLoader(host, 'user', 'pw')
    with pytest.raises(ExitDueToError):
        getattr(autoloader, '_query')('')
    log = caplog.records()[-1].message
    expected = 'URL "{}" is invalid: {}'.format(
        'http://{}/'.format(host),
        '<urlopen error [Errno 8] nodename nor servname provided, or not known>',
    )
    assert log == expected
