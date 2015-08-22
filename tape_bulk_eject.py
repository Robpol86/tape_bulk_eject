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
import HTMLParser
import json
import logging
import os
import re
import signal
import sys
import time
import urllib2

__author__ = '@Robpol86'
__license__ = 'MIT'


class HandledError(Exception):
    """Raised on a handled error Causes exit code 1.

    Any other exception raised is considered a bug.
    """

    pass


class AutoloaderError(Exception):
    """Raised when the autoloader replies with HTTP 401.

    The stupid thing uses 401 for everything. Invalid credentials, locked drive, bad request data,
    and even rate limiting.
    """

    pass


class InfoFilter(logging.Filter):
    """Filter out non-info and non-debug logging statements.

    From: https://stackoverflow.com/questions/16061641/python-logging-split/16066513#16066513
    """

    def filter(self, record):
        """Filter method.

        :param record: Log record object.

        :return: Keep or ignore this record.
        :rtype: bool
        """
        return record.levelno <= logging.INFO


class TapePos(HTMLParser.HTMLParser):
    """Parses commands.html and gets current tape positions.

    :cvar RE_ONCLICK: <img /> onclick attribute parser (e.g. onClick="from_to(mailslot)").

    :ivar bool in_center_tag: If parser is within <center /> on the page. There's only one.
    :ivar dict inventory: Populates this with the current inventory parsed from HTML.
    """

    RE_ONCLICK = re.compile(r'from_to\((?:slot(\d+)|(drive|picker|mailslot))\)')

    def __init__(self, inventory):
        """Constructor."""
        HTMLParser.HTMLParser.__init__(self)
        self.in_center_tag = False
        self.inventory = inventory

    def handle_starttag(self, tag, attrs):
        """Called on all starting tags.

        :param str tag: Current HTML tag (e.g. 'center' or 'img').
        :param list attrs: List of attributes (key value pairs) on this HTML tag.
        """
        if tag == 'center':
            self.in_center_tag = True
        elif tag == 'img' and self.in_center_tag:
            attributes = dict(attrs)
            if 'onclick' in attributes and 'title' in attributes:
                self.update_slot(attributes)

    def handle_endtag(self, tag):
        """Called on all ending/closing tags.

        :param str tag: Current HTML tag (e.g. 'center' or 'img').
        """
        if tag == 'center':
            self.in_center_tag = False

    def update_slot(self, attrs):
        """Update self.inventory with current state of a single slot.

        :raise HandledError: On handled errors. Logs before raising. Program should exit.

        :param dict attrs: Attributes of <img /> tag representing a slot.
        """
        logger = logging.getLogger('TapePos.update_slot')
        logger.debug('img tag attributes: %s', str(attrs))
        onclick, tape = attrs['onclick'], attrs['title']
        if tape == 'Empty':
            return
        try:
            slot = [i for i in self.RE_ONCLICK.match(onclick).groups() if i][0]
        except AttributeError:
            logger.error('Attribute "onclick" in img tag is invalid: %s', onclick)
            raise HandledError
        self.inventory[tape] = slot


class Autoloader(object):
    """Interfaces with the autoloader over its HTTP web interface.

    :cvar int DELAY: Number of seconds to wait between queries. The web interface is very fragile.
    :cvar int DELAY_ERROR: Number of seconds to wait if we get an error from the autoloader.

    :ivar str auth: HTTP basic authentication credentials (base64 encoded).
    :ivar dict inventory: Tape positions. 16 slots + drive (17), picker (18), and mail slot (19).
    :ivar float last_access: Unix time of last HTTP query.
    :ivar str url: URL prefix of the autoloader (e.g. 'http://192.168.0.50/').
    """

    DELAY = 10
    DELAY_ERROR = 15

    def __init__(self, host_name, user_name, pass_word):
        """Constructor.

        :param str host_name: Hostname or IP address of the autoloader.
        :param str user_name: HTTP username (e.g. 'admin').
        :param str pass_word: HTTP password.
        """
        self.auth = base64.standard_b64encode(':'.join((user_name, pass_word)))
        self.inventory = dict()
        self.last_access = time.time() - self.DELAY
        self.url = 'http://{}/'.format(host_name)

    def _query(self, request, no_delay=False):
        """Query the autoloader's web interface. Enforces delay timer.

        :raise HandledError: On handled errors. Logs before raising. Program should exit.
        :raise AutoloaderError: On HTTP 401 errors when querying the web interface.

        :param urllib2.Request request: urllib2.Request instance with data/headers already added.
        :param bool no_delay: Exclude this query from sleeping and updating last_access.

        :return: HTML response payload.
        :rtype: str
        """
        logger = logging.getLogger('Autoloader._query')
        if not no_delay:
            sleep_for = max(0, self.DELAY - (time.time() - self.last_access))
            if sleep_for:
                logger.debug('Sleeping for %d second(s).', sleep_for)
                time.sleep(sleep_for)
                logger.debug('Done sleeping.')
            self.last_access = time.time()
            logger.debug('Set last_access to %f', self.last_access)

        # Send request and get response.
        try:
            response = urllib2.urlopen(request)
        except urllib2.HTTPError as exc:
            url = request.get_full_url()
            if exc.code == 404:
                logger.error('404 Not Found on: %s', url)
            elif exc.code == 401:
                logger.debug('401 Unauthorized on: %s', url)
                raise AutoloaderError
            else:
                logger.error('%s returned HTTP %s instead of 200.', url, exc.code)
            raise HandledError
        except urllib2.URLError as exc:
            url = request.get_full_url()
            logger.error('URL "%s" is invalid: %s', url, str(exc))
            raise HandledError

        html = response.read(102400)
        logger.debug('Got HTML from autoloader: %s', html)
        return html

    def check_creds(self):
        """Check credentials by going to config_opts.html. Doesn't change anything.

        :raise HandledError: On handled errors. Logs before raising. Program should exit.
        """
        logger = logging.getLogger('Autoloader.auth')
        request = urllib2.Request(self.url + 'config_ops.html')
        request.headers['Authorization'] = 'Basic {}'.format(self.auth)
        try:
            self._query(request, no_delay=True)
        except AutoloaderError:
            message = '%s 401 Unauthorized. Possibly rate limiting or invalid credentials.'
            logger.error(message, request.get_full_url())
            raise HandledError

    def eject(self, tape):
        """Perform tape move to the mailslot thereby "ejecting" it.

        Blocks during entire move operation. Once done self.inventory is updated.

        :param str tape: The tape to eject.
        """
        logger = logging.getLogger('Autoloader.eject')
        slot = self.inventory[tape]
        slot = int(dict(drive=17, mailslot=18, picker=19).get(slot, slot))
        data = 'from={}&to=18&submit=submit'.format(slot)
        logger.debug('Eject POST data: %s', data)
        request = urllib2.Request(self.url + 'move.cgi', data)
        request.headers['Authorization'] = 'Basic {}'.format(self.auth)
        request.headers['Content-type'] = 'application/x-www-form-urlencoded'
        request.headers['Origin'] = self.url.rstrip('/')
        request.headers['Referer'] = self.url + 'commands.html'

        # Eject tape.
        while True:
            try:
                html = self._query(request)
            except AutoloaderError:
                logger.warning('Error while ejecting. Retrying in %s seconds...', self.DELAY_ERROR)
                time.sleep(self.DELAY_ERROR)
                continue
            self.update_inventory(html)
            if tape not in self.inventory or self.inventory[tape] == 'mailslot':
                break
            if self.inventory[tape] == 'drive':
                logger.warning('Failed, drive locked? Retrying in %s seconds...', self.DELAY_ERROR)
            else:
                logger.warning('Tape did not move. Retrying in %s seconds...', self.DELAY_ERROR)
            time.sleep(self.DELAY_ERROR)

    def update_inventory(self, html=None):
        """Get current tape positions in the autoloader and updates self.inventory.

        :raise HandledError: On handled errors. Logs before raising. Program should exit.

        :param str html: Parse this html if set. Otherwise requests HTML from autoloader.
        """
        logger = logging.getLogger('Autoloader.update_inventory')
        if not html:
            request = urllib2.Request(self.url + 'commands.html')
            html = self._query(request)
        if not TapePos.RE_ONCLICK.search(html):
            logger.error('Invalid HTML, found no regex matches.')
            raise HandledError
        parser = TapePos(self.inventory)
        self.inventory.clear()
        parser.feed(html)
        logger.debug('Loaded tapes: %s', '|'.join(sorted(self.inventory)))


def get_arguments(argv=None):
    """Get command line arguments.

    :param list argv: Command line argument list to process.

    :return: Argparse Namespace object.
    """
    program = os.path.basename(__file__).replace('.pyc', '.py')
    parser = argparse.ArgumentParser(prog=program, description=__doc__)
    parser.add_argument('-v', '--verbose', action='store_true', help='Print debug messages.')
    parser.add_argument('tapes', nargs='+', metavar='TAPE', type=str,
                        help='list of tapes, space or | delimited.')
    return parser.parse_args(args=argv if argv is not None else sys.argv[1:])


def setup_logging(arguments, logger=None):
    """Setup console logging. Info and below go to stdout, others go to stderr.

    :param arguments: Argparse Namespace object from get_arguments().
    :param str logger: Which logger to set handlers to. Used for testing.

    :return: Same Argparse Namespace object in arguments.
    """
    verbose = arguments.verbose
    format_ = '%(asctime)s %(levelname)-8s %(name)-20s %(message)s' if verbose else '%(message)s'
    level = logging.DEBUG if verbose else logging.INFO

    handler_stdout = logging.StreamHandler(sys.stdout)
    handler_stdout.setFormatter(logging.Formatter(format_))
    handler_stdout.setLevel(logging.DEBUG)
    handler_stdout.addFilter(InfoFilter())

    handler_stderr = logging.StreamHandler(sys.stderr)
    handler_stderr.setFormatter(logging.Formatter(format_))
    handler_stderr.setLevel(logging.WARNING)

    root_logger = logging.getLogger(logger)
    root_logger.setLevel(level)
    root_logger.addHandler(handler_stdout)
    root_logger.addHandler(handler_stderr)

    return arguments


def combine_config(arguments):
    """Read configuration file and validate command line arguments.

    :raise HandledError: On handled errors. Logs before raising. Program should exit.

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
        raise HandledError
    logger.debug('Got: %s', str(tapes))

    # Read config file.
    json_file = os.path.join(os.path.expanduser('~'), '.pv124t.json')
    logger.debug('Reading: %s', json_file)
    try:
        with open(json_file) as handle:
            json_file_data = handle.read(1024)
    except IOError as exc:
        logger.error('Failed to read %s: %s', json_file, str(exc))
        raise HandledError
    logger.debug('Got: %s', json_file_data)

    # Parse config file json.
    try:
        json_parsed = json.loads(json_file_data)
    except ValueError as exc:
        logger.error('Failed to parse json in %s: %s', json_file, exc.message)
        raise HandledError
    logger.debug('Got: %s', str(json_parsed))

    # Read values from json.
    try:
        host_name = json_parsed['host']
        user_name = json_parsed['user']
        pass_word = json_parsed['pass']
    except TypeError:
        logger.error('JSON data not a dictionary.')
        raise HandledError
    except KeyError as exc:
        logger.error('Missing key from JSON dict: %s', exc.message)
        raise HandledError

    # Catch empty values.
    if not all((host_name, user_name, pass_word)):
        logger.error('One or more JSON value is empty.')
        raise HandledError

    return {'tapes': tapes, 'host': host_name, 'user': user_name, 'pass': pass_word}


def main(config):
    """Main function of program.

    :param dict config: Parsed command line and config file data.
    """
    logger = logging.getLogger('main')
    logger.info('Connecting to autoloader and reading tape inventory...')
    autoloader = Autoloader(config['host'], config['user'], config['pass'])
    autoloader.check_creds()
    autoloader.update_inventory()

    # Purge missing tapes.
    tapes = list()
    for tape in config['tapes']:
        if tape not in autoloader.inventory:
            logger.info('%s not in autoloader, skipping.', tape)
            continue
        if autoloader.inventory[tape] == 'mailslot':
            logger.error('%s already in mailslot, skipping.', tape)
            continue
        tapes.append(tape)
    if not tapes:
        logging.info('No tapes to eject. Nothing to do.')
        return

    while tapes:
        # Make sure mailslot and picker are clear.
        blockers = sorted(s for s in autoloader.inventory.values() if s in ('mailslot', 'picker'))
        if blockers:
            logger.info('Tape in %s, remove to continue...', blockers[0])
            autoloader.update_inventory()
            continue

        # Eject.
        tape = tapes.pop()
        left = len(tapes)
        logger.info('Ejecting %s (%d other%s left)...', tape, left, '' if left == 1 else 's')
        autoloader.eject(tape)

    total = len(config['tapes'])
    logger.info('Ejected %d tape%s.', total, '' if total == 1 else 's')


if __name__ == '__main__':
    signal.signal(signal.SIGINT, lambda *_: getattr(os, '_exit')(0))  # Properly handle Control+C.
    try:
        main(combine_config(setup_logging(get_arguments())))
    except HandledError:
        logging.critical('EXITING DUE TO ERROR!')
        sys.exit(1)
    logging.info('Success.')
