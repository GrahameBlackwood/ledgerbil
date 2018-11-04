import os
import subprocess
import sys

from ..settings_getter import get_setting


def get_ledger_command(args=None):
    files = []
    for f in get_setting('LEDGER_FILES'):
        files += ['-f', os.path.join(get_setting('LEDGER_DIR'), f)]
    return get_setting('LEDGER_COMMAND') + tuple(files) + (args or ())


def get_ledger_output(args=None):
    cmd = get_ledger_command(args)
    process = subprocess.Popen(cmd, stdout=subprocess.PIPE)
    output, error = process.communicate()
    if error:   # todo: return output, _ and don't bother with error - if
                # an error, we'll see it since we didn't send to pipe...
        print(error)
        sys.exit(1)
    return output.decode('unicode_escape').rstrip()
