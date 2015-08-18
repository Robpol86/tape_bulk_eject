#!/usr/bin/env python2.7
"""Eject multiple tapes from a Dell PowerVault 124T autoloader in one go.

No way to do this over SCSI. Instead this works over HTTP through the
autoloader's web interface. From: https://github.com/Robpol86/tape_bulk_eject

Supply credentials through ~/.pv124t.json:
{
    "host": "192.168.0.50",
    "user": "admin",
    "pass": "super_secret_password"
}
"""

from __future__ import print_function

import argparse
import base64
import json
import logging
import os
import signal
import sys
import time
import urllib
import urllib2

__author__ = '@Robpol86'
__license__ = 'MIT'


class ExitDueToError(Exception):
    """Raised on a handled error Causes exit code 1.

    Any other exception raised is considered a bug.
    """

    pass


class AutoLoader(object):
    """Interfaces with the autoloader over its HTTP web interface.

    :cvar int DELAY: Number of seconds to wait between queries. The web interface is very fragile.

    :ivar str url: URL prefix of the autoloader (e.g. 'http://192.168.0.50/').
    :ivar str auth: HTTP basic authentication credentials (base64 encoded).
    :ivar dict inventory: Tape positions. 16 slots + drive (17), picker (18), and mail slot (19).
    :ivar int _last_access: Unix time of last HTTP query.
    """

    DELAY = 10

    def __init__(self, host_name, user_name, pass_word):
        """Constructor.

        :param str host_name: Hostname or IP address of the autoloader.
        :param str user_name: HTTP username (e.g. 'admin').
        :param str pass_word: HTTP password.
        """
        self.url = 'http://{}/'.format(host_name)
        self.auth = base64.standard_b64encode(':'.join((user_name, pass_word)))

        keys = [str(i) for i in range(1, 17)] + ['drive', 'picker', 'mailslot']
        self.inventory = {k: '' for k in keys}

        self._last_access = int(time.time()) - self.DELAY

    def _query(self, page, data=None, headers=None):
        """Query the autoloader's web interface. Enforces delay timer.

        :param str page: Suffix of the url (e.g. 'commands.html').
        :param dict data: POST data to send.
        :param dict headers: HTTP headers to include in the request.

        :return: HTML response payload.
        :rtype: str
        """
        logger = logging.getLogger('AutoLoaderInterface._query')
        sleep_for = max(0, self.DELAY - (int(time.time()) - self._last_access))
        if sleep_for:
            logger.debug('Sleeping for %d second(s).', sleep_for)
            time.sleep(sleep_for)
            logger.debug('Done sleeping.')

        # Prepare request.
        url = self.url + page
        logger.debug('Building request for: %s', url)
        request = urllib2.Request(url)
        if data:
            logger.debug('Encoding data: %s', str(data))
            data_encoded = urllib.urlencode(data)
            logger.debug('Adding encoded data: %s', data_encoded)
            request.add_data(data_encoded)
        headers = headers or dict()
        headers['Authorization'] = 'Basic {}'.format(self.auth)
        for key, value in headers.iteritems():
            logger.debug('Adding "%s" header: %s', key, value)
            request.add_header(key, value)

        # Send request and get response.
        response = urllib2.urlopen(request)  # TODO error handle.
        html = response.read(10240)
        return html

    def eject(self):
        """Todo.

        :return:
        """
        pass

    def update_inventory(self):
        """Todo.

        :return:
        """
        html = self._query('commands.html')
        assert html  # TODO


def get_arguments(argv=None):
    """Get command line arguments.

    :param list argv: Command line argument list to process.

    :return: Argparse Namespace object.
    """
    prog = os.path.basename(__file__).replace('.pyc', '.py')
    parser = argparse.ArgumentParser(prog=prog, description=__doc__)
    parser.add_argument('-v', '--verbose', action='store_true', help='Print debug messages.')
    parser.add_argument('tapes', nargs='+', metavar='TAPE', type=str,
                        help='list of tapes, space or | delimited.')
    return parser.parse_args(args=argv if argv is not None else sys.argv[1:])


def setup_logging(arguments):
    """Setup console logging. Info and below go to stdout, others go to stderr.

    :param arguments: Argparse Namespace object from get_arguments().

    :return: Same Argparse Namespace object in arguments.
    """
    verbose = arguments.verbose
    format_ = '%(asctime)s %(levelname)-8s %(name)-20s %(message)s' if verbose else '%(message)s'
    level = logging.DEBUG if verbose else logging.INFO

    handler_stdout = logging.StreamHandler(sys.stdout)
    handler_stdout.setFormatter(logging.Formatter(format_))
    handler_stdout.setLevel(logging.DEBUG)
    handler_stdout.addFilter(
        type('Filter2', (logging.Filter, ), {'filter': lambda _, rec: rec.levelno <= logging.INFO})
    )

    handler_stderr = logging.StreamHandler(sys.stderr)
    handler_stderr.setFormatter(logging.Formatter(format_))
    handler_stderr.setLevel(logging.WARNING)

    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    root_logger.addHandler(handler_stdout)
    root_logger.addHandler(handler_stderr)

    return arguments


def combine_config(arguments):
    """Read configuration file and validate command line arguments.

    :param arguments: Argparse Namespace object from get_arguments().

    :return: User input data.
    :rtype: dict
    """
    logger = logging.getLogger('combine_config')

    # Get list of tapes from arguments.
    logger.debug('Reading arguments.tapes: %s', str(arguments.tapes))
    tapes = sorted(set('|'.join(arguments.tapes).replace(' ', '|').strip().strip('|').split('|')))
    if not tapes or not all(tapes):
        logger.error('No tapes specified.')
        raise ExitDueToError
    logger.debug('Got: %s', str(tapes))

    # Read config file.
    json_file = os.path.join(os.path.expanduser('~'), '.pv124t.json')
    logger.debug('Reading: %s', json_file)
    try:
        with open(json_file) as handle:
            json_file_data = handle.read(1024)
    except IOError as exc:
        logger.error('Failed to read %s: %s', json_file, str(exc))
        raise ExitDueToError
    logger.debug('Got: %s', json_file_data)

    # Parse config file json.
    try:
        json_parsed = json.loads(json_file_data)
    except ValueError as exc:
        logger.error('Failed to parse json in %s: %s', json_file, exc.message)
        raise ExitDueToError
    logger.debug('Got: %s', str(json_parsed))

    # Read values from json.
    try:
        host_name = json_parsed['host']
        user_name = json_parsed['user']
        pass_word = json_parsed['pass']
    except TypeError:
        logger.error('JSON data not a dictionary.')
        raise ExitDueToError
    except KeyError as exc:
        logger.error('Missing key from JSON dict: %s', exc.message)
        raise ExitDueToError

    # Catch empty values.
    if not all((host_name, user_name, pass_word)):
        logger.error('One or more JSON value is empty.')
        raise ExitDueToError

    return {'tapes': tapes, 'host': host_name, 'user': user_name, 'pass': pass_word}


def main(config):
    """Main function of program.

    :param dict config: Parsed command line and config file data.
    """
    logger = logging.getLogger('main')
    assert config  # TODO
    assert logger  # TODO


if __name__ == '__main__':
    signal.signal(signal.SIGINT, lambda *_: getattr(os, '_exit')(0))  # Properly handle Control+C.
    try:
        main(combine_config(setup_logging(get_arguments())))
    except ExitDueToError:
        logging.critical('EXITING DUE TO ERROR!')
        sys.exit(1)
    logging.info('Success.')
