import logging
import time

import pytest

from tape_bulk_eject import setup_logging


@pytest.mark.parametrize('verbose', [True, False])
def test(capsys, verbose):
    logger = 'test_logger_{}'.format(verbose)
    arguments = type('', (), {'verbose': verbose})
    assert setup_logging(arguments, logger) == arguments

    log = logging.getLogger(logger)
    for a in ('debug', 'info', 'warning', 'error', 'critical'):
        getattr(log, a)('Test {}.'.format(a))
        time.sleep(0.01)
    stdout, stderr = capsys.readouterr()

    if verbose:
        assert logger in stdout
        assert logger in stderr
        assert 'Test debug.' in stdout
    else:
        assert logger not in stdout
        assert logger not in stderr
        assert 'Test debug.' not in stdout
    assert 'Test debug.' not in stderr

    assert 'Test info.' in stdout
    assert 'Test warning.' not in stdout
    assert 'Test error.' not in stdout
    assert 'Test critical.' not in stdout

    assert 'Test info.' not in stderr
    assert 'Test warning.' in stderr
    assert 'Test error.' in stderr
    assert 'Test critical.' in stderr
