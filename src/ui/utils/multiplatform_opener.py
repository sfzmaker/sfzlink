# -*- coding: utf-8 -*-
# ------------------------------------------------------
# Author: Ytturi
# Author's e-mail: ytturi@protonmail.com
# Original Gist: https://gist.github.com/ytturi/0c23ad5ab89154d24c340c2b1cc3432b
# Version: 0.1
# License: MIT
# ------------------------------------------------------
# This script allows the user to run the default program
# to open a file for it's given type or extension.
#
# It contains the `subprocess_open` method that calls 
# for the program in a subprocess using subprocess' Popen.
#
# But also the `get_open_command` that returns the
# script to run in a shell so you can call it as you want.
#
# If you want to test it, you can use this same script to
# open the file. 
# Note that "click" is required in order to test it.
# ------------------------------------------------------

from subprocess import Popen, PIPE
from subprocess import check_output
from platform import system


OSNAME = system().lower()


def get_open_command(filepath):
    """
    Get the console-like command to open the file
    for the current platform:
    - Windows: "start {{ filepath }}"
    - OS X: "open {{ filepath }}"
    - Linux based (wdg): "wdg-open {{ filepath }}"
    :param filepath:    Path to the file to be opened
    :type filepath:     string
    :return:            Command to run from a shell
    :rtype:             string
    """
    if 'windows' in OSNAME:
        opener = 'start'
    elif 'osx' in OSNAME or 'darwin' in OSNAME:
        opener = 'open'
    else:
        opener = 'xdg-open'
    return f'{opener} {filepath}'


def subprocess_opener(filepath):
    """
    Method to open the file with the default program in a subprocess.
    As being called in a subprocess, it will not block the current one.
    This method runs the command on a subprocess using the default system shell.
    Check the docs of subprocess module for more info:
    https://docs.python.org/2/library/subprocess.html#subprocess.Popen
    The subprocess will run in background so you won't be able to bring back
    the result code, but the current log can be obtained via the Popen's PIPE:
    Usage:
    ```
    # Run as subprocess
    subproc = subprocess_opener(filepath)
    # Get the stdout for the subprocess
    print(subproc.stdout)
    # Get the stderr for the subprocess
    print(subproc.stderr)
    ```
    :type filepath:     string
    :param filepath:    Path to the file to open
    :rtype:             subprocess
    :return:            The pointer the subprocess returned by the Popen call
    """
    subproc = Popen(
        get_open_command(filepath),
        stdout=PIPE, stderr=PIPE, shell=True
    )
    subproc.wait()
    return subproc