#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# SPDX-License-Identifier: MIT

"""
Backup multiple iOS (iPhone/iPad) devices regularly.

For documentation visit: https://github.com/yoshtec/krummstiel
"""

# TODO: evaluate and use python bindings of libimobiledevice https://github.com/upbit/python-imobiledevice_demo

import shlex
import sys
import shutil
import os
import click
import pprint as p
from pathlib import Path
from click_default_group import DefaultGroup
from .metadata import cat_metadata_files, IOSPhotosDB, list_albums

ENC = "utf-8"


class Operation:
    def __init__(self, debug=None, info=print, warn=print, error=print):
        self._debug: callable = debug
        self._info: callable = info
        self._warn: callable = warn
        self._error: callable = error

    def error(self, msg):
        if self._error:
            self._error(msg)

    def info(self, msg):
        if self._info:
            self._info(msg)

    def warn(self, msg):
        if self._warn:
            self._warn(msg)

    def debug(self, msg):
        if self._debug:
            self._debug(msg)

    def call(self, args, ignore_return_code=False):
        import subprocess

        cmd_str = " ".join(args)
        self.debug(f"Execute command: '{cmd_str}'")
        p = subprocess.Popen(
            args,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding=ENC,
        )
        stdout, stderr = p.communicate()
        if stdout:
            self.debug(f"stdout: \n{stdout}")
        if stderr:
            self.debug(f"stderr: \n{stderr}")
        if not ignore_return_code and p.returncode != 0:
            raise RuntimeError(f"failed to run '{cmd_str}'")
        return stdout


class MiDevice:
    def __init__(
        self,
        uid: str,
        base_path: Path = None,
        alias: str = None,
        exclude=None,
        op=Operation(),
    ):

        self.uid: str = uid

        if not op:
            op = Operation()
        self.op: Operation = op

        self.is_present: bool = self._is_present()

        if not alias:
            alias = self.get_name()
        self.alias: str = alias

        if exclude is None:
            exclude = []
        self.exclude = exclude

        # computed properties
        self.target: Path = None
        self._mount_point: Path = None
        if base_path:
            self.target = base_path.joinpath(self.alias).resolve()

            self._mount_point = (
                base_path.joinpath(".mount").joinpath(self.uid).resolve()
            )

        self.is_mounted: bool = False

    def _is_present(self):
        try:
            devices = self.op.call(["idevice_id", "-l"])
            return self.uid in devices
        except RuntimeError as e:
            self.op.error(f"error while checking for devices {e}")
        return False

    def is_cooled_down(self, minutes=0):
        if self.target:
            import time

            return time.time() - self.target.lstat().st_mtime > minutes * 60
        return False

    def get_name(self):
        if not self.is_present:
            return None
        try:
            info = self.op.call(
                ["ideviceinfo", "--key", "DeviceName", "-u", shlex.quote(self.uid)]
            )
            return info
        except RuntimeError as e:
            self.op.info(f"could not retrieve name of device uid={self.uid}, error {e}")

    def mount(self):
        if not self.is_present or not self._mount_point:
            self.op.debug(f"will not mount device {self.uid} while path was missing")
            return

        try:
            self._mount_point.mkdir(parents=True, exist_ok=True)
            cmd = ["ifuse", "-u", shlex.quote(self.uid), str(self._mount_point)]
            self.op.call(cmd)
            self.is_mounted = True
            self.op.info(f"device {self.alias} mounted at {self._mount_point}")
        except RuntimeError as e:
            self.op.error(f"Error while mounting: {e}")

    def umount(self):
        if not self.is_mounted:
            return

        try:
            cmd = ["umount", str(self._mount_point)]
            self.op.call(cmd)
            self.is_mounted = False
        except RuntimeError as e:
            self.op.error(f"Error while unmounting {self._mount_point}, with {e}")
            self.op.error("Do not unplug the iOS device while Backup is running")
            self.op.error("try running:")
            self.op.error(f"    sudo umount --force {self._mount_point}")

    def backup(self, verbose=False):
        if not self.is_mounted:
            self.op.info(f"cannot backup {self.alias}: device not mounted")
            return

        try:
            self.op.info(f"backing up device {self.alias} to {self.target}")
            if not self.target.exists():
                self.target.mkdir(parents=True, exist_ok=True)
            else:
                # set last modification time to the begin of backup time
                self.target.touch()

            cmd = ["rsync", "-ah"]
            if verbose:
                cmd.extend(["-v"])
            for e in self.exclude:
                cmd.extend(["--exclude", shlex.quote(e)])
            cmd.extend([f"{self._mount_point}{os.sep}", str(self.target)])
            self.op.call(cmd)
            self.op.info("finished backup")
        except RuntimeError as e:
            self.op.error(f"error while backup of {self.alias}: {e}")

    def prune_photos(self):
        if not self.is_mounted:
            self.op.debug(f"cannot prune {self.alias}: device not mounted")
            return

        # cleanup of iphone: delete photos and videos of certain age
        # except if in favourites

        # https://simonwillison.net/2020/May/21/dogsheep-photos/

        pass

    def notify(self):
        # TODO push notification to the device backup has finished or alternatively send mail etc..
        # send owner a note that it was synced
        #  - could be a pic with the info inside
        pass

    def check_paired(self):
        try:
            devices = self.op.call(["idevicepair", "list"])
            return self.uid in devices
        except RuntimeError as e:
            self.op.error(
                f"Error while checking if {self.uid} is paired with this host: {e}"
            )
        return False

    def pair(self):
        try:
            # have to wait for user interaction.
            cmd = ["idevicepair", "-u", shlex.quote(self.uid), "pair"]
            self.op.call(cmd)
        except RuntimeError as e:
            self.op.error(e)

    @classmethod
    def discover(cls, op=Operation()):
        if op:
            return op.call(["idevice_id", "-l"])

    def __del__(self):
        self.umount()

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.umount()


@click.group(
    cls=DefaultGroup,
    default="backup",
    default_if_no_args=True,
)
def cli():
    """This is the krummstiel iOS Backup tool! Backup your ios devices or examine metadata
    files and information of your ios device"""
    pass


@cli.command()
@click.option(
    "--config",
    "-c",
    required=True,
    help="use this config file",
)
@click.option(
    "--discover",
    "-d",
    default=False,
    is_flag=True,
    help="List devices that are currently connected, that are not in your config file. "
    "Prints configuration stub for the config file",
)
@click.option(
    "--verbose",
    "-v",
    help="verbose output, increase amount to increase verbosity",
    count=True,
    default=0,
)
def backup(config=None, discover=False, verbose=0):
    """Regularly backup multiple iOS devices."""
    import configparser

    op = Operation()
    if verbose > 0:
        op = Operation(debug=print, error=print, info=print)
        op.debug("entering verbose mode")

    # Check for prereq
    required_commands = [
        "idevicepair",
        "ifuse",
        "rsync",
        "umount",
        "idevice_id",
        "ideviceinfo",
    ]
    has_error = False
    for cmd in required_commands:
        if shutil.which(cmd) is None:
            op.error(f"cmd: {cmd} is missing")
            has_error = True

    if has_error:
        op.error(f"Requirements are missing! please install e.g.:")
        op.error(f"    apt install libimobiledevice-utils rsync ifuse ")
        sys.exit(1)

    if config:
        conf = configparser.ConfigParser()
        conf.read(config)

        if len(conf.sections()) == 0:
            op.warn(f"Warning: config file '{conf}' is empty or not existent")
            has_error = True

        if discover:
            for dev in MiDevice.discover(op=op).splitlines():
                if not conf.has_section(dev):
                    device = MiDevice(uid=dev, op=op)
                    device_name = device.get_name()
                    device_paired = device.check_paired()

                    op.info(f"new device discovered: {dev}")
                    op.info("Add to your config file:")
                    op.info("---")
                    op.info(f"[{dev}]")
                    op.info(f"name = {device_name}")
                    op.info("---")
                    op.info("")
                    if not device_paired:
                        op.info("Also pair your device by executing:")
                        op.info(f"    idevicepair -u {dev}")
                    else:
                        op.info("device is already paired")
            return 0

        for s in conf.sections():

            name = conf.get(s, "name", fallback=None)
            if name is None:
                op.error(
                    f"config error: 'name' tag is missing from config section: [{s}]"
                )
                has_error = True
                continue

            if conf.getboolean(s, "ignore", fallback=False):
                op.info(f"ignoring device '{name}' with uid={s}")
                continue

            backup_path = conf.get(s, "backup_path", fallback=None)
            if backup_path is None:
                op.error(
                    f"config error: backup_path is missing from config section [{s}] or in [DEFAULT] section"
                )
                has_error = True
                continue
            backup_path = Path(backup_path)

            exclude = conf.get(s, "exclude", fallback=None)
            if exclude is not None:
                if exclude.startswith("[") and exclude.endswith("]"):
                    import json

                    try:
                        exclude = json.loads(exclude)
                    except RuntimeError as e:
                        op.error(
                            f"config error: error reading exclude array from config section [{s}], error={e}"
                        )
                        op.error(f"stopping backup for device '{name}' with uid='{s}' ")
                        has_error = True
                        continue
                else:
                    # only single to exclude
                    exclude = [exclude]

            device = MiDevice(
                uid=s, base_path=backup_path, alias=name, exclude=exclude, op=op
            )

            if not device.is_present:
                op.info(f"device '{name}' with uid={s} not connected. skipping!")
                continue

            if not device.check_paired():
                op.info(
                    f"please pair your device '{device.alias}' uid={device.uid} by executing:"
                )
                op.info(f"    idevicepair -u {device.uid}")
                continue

            cool_down_period = conf.getint(s, "cool_down_period", fallback=0)
            if not device.is_cooled_down(cool_down_period):
                op.info(f"device '{name}' with uid={s} not cooled down. skipping!")

            device.mount()
            device.backup(verbose=verbose >= 2)

            if conf.getboolean(s, "prune_photos", fallback=False):
                device.prune_photos()

            device.umount()
            device.notify()

    if has_error:
        sys.exit(1)

    return 0


@cli.command()
@click.argument(
    "files", nargs=-1, type=click.Path(exists=True, file_okay=True, readable=True)
)
@click.option(
    "--raw", "-R", default=False, is_flag=True, help="also print raw plist contents"
)
@click.option(
    "--recurse",
    "-r",
    default=False,
    is_flag=True,
    help="recurse into subdirs, reads all files ignores non plist files",
)
def cat_md(files=None, raw=False, recurse=False):
    """
    display contents of plist metadata files. helps to understand where and how data
    is stored on your ios device. Reads and displays:

    \b
        *.albummetadata
        *.memorymetadata
        *.facemetadata
        *.foldermetadata

    and general .plist like files.
    """
    sys.exit(cat_metadata_files(file=files, raw=raw, recurse=recurse))


@cli.command()
@click.argument("db_file", type=click.Path(exists=True, file_okay=True, dir_okay=False))
def db(db_file=None):
    list_albums(db_file)


if "__main__" == __name__:
    sys.exit(cli())
