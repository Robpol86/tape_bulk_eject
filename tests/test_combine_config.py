import pytest

from tape_bulk_eject import combine_config, get_arguments, ExitDueToError


def test_bad_args(caplog):
    args = get_arguments([''])
    with pytest.raises(ExitDueToError):
        combine_config(args)
    log = caplog.records()[-1].message
    assert log == 'No tapes specified.'


def test_remainder(monkeypatch, tmpdir, caplog):
    pv124t_json = tmpdir.join('.pv124t.json')
    monkeypatch.setattr('os.path.expanduser', lambda _: str(tmpdir))
    args = get_arguments(['A00001L3'])
    with pytest.raises(ExitDueToError):
        combine_config(args)
    log = caplog.records()[-1].message
    expected = 'Failed to read {}: {}'.format(
        str(pv124t_json),
        "[Errno 2] No such file or directory: '{}'".format(str(pv124t_json)),
    )
    assert log == expected

    pv124t_json.ensure()  # Create empty file.
    with pytest.raises(ExitDueToError):
        combine_config(args)
    log = caplog.records()[-1].message
    expected = 'Failed to parse json in {}: {}'.format(
        str(pv124t_json),
        'No JSON object could be decoded',
    )
    assert log == expected

    pv124t_json.write('\x00\x01\x02\x03')  # Write binary garbage.
    with pytest.raises(ExitDueToError):
        combine_config(args)
    log = caplog.records()[-1].message
    expected = 'Failed to parse json in {}: {}'.format(
        str(pv124t_json),
        'No JSON object could be decoded',
    )
    assert log == expected

    for json in ('[]', '0', '0.1', 'false', 'null', '"test"'):
        pv124t_json.write(json)  # Unexpected valid JSON. Should be a dict.
        with pytest.raises(ExitDueToError):
            combine_config(args)
        log = caplog.records()[-1].message
        assert log == 'JSON data not a dictionary.'

    pv124t_json.write('{}')  # Missing key.
    with pytest.raises(ExitDueToError):
        combine_config(args)
    log = caplog.records()[-1].message
    assert log == 'Missing key from JSON dict: host'

    pv124t_json.write('{"host": "", "user": "user", "pass": "pass"}')  # Empty value.
    with pytest.raises(ExitDueToError):
        combine_config(args)
    log = caplog.records()[-1].message
    assert log == 'One or more JSON value is empty.'

    pv124t_json.write('{"host": "192.168.0.50", "user": "admin", "pass": "password"}')
    actual = combine_config(args)
    expected = {'host': '192.168.0.50', 'user': 'admin', 'pass': 'password', 'tapes': ['A00001L3']}
    assert actual == expected

    args = get_arguments(['A00002L3|A00002L3|A00001L3', 'A00005L3|A00004L3', 'A00003L3'])
    actual = combine_config(args)
    expected['tapes'] = ['A00001L3', 'A00002L3', 'A00003L3', 'A00004L3', 'A00005L3']
    assert actual == expected
