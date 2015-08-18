import pytest

from tape_bulk_eject import combine_config, get_arguments, ExitDueToError


def test_bad_args(caplog):
    args = get_arguments([''])
    with pytest.raises(ExitDueToError):
        combine_config(args)
    logs = caplog.text()
    assert logs.endswith('No tapes specified.\n')
