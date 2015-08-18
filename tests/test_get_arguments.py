import pytest

from tape_bulk_eject import get_arguments


def test(capsys):
    with pytest.raises(SystemExit):
        get_arguments(argv=[])
    stderr = capsys.readouterr()[1]
    assert 'tape_bulk_eject.py: error: too few arguments\n' in stderr

    arguments = get_arguments(argv=['A00001L3|A00002L3|A00003L3', 'A00004L3'])
    assert arguments.verbose is False
    assert arguments.tapes == ['A00001L3|A00002L3|A00003L3', 'A00004L3']

    arguments = get_arguments(argv=['-v', 'A00001L3|A00002L3|A00003L3'])
    assert arguments.verbose is True
    assert arguments.tapes == ['A00001L3|A00002L3|A00003L3']
