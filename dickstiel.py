#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# SPDX-License-Identifier: MIT

"""

"""

# TODO: evaluate and use python bindings of libimobiledevice https://github.com/upbit/python-imobiledevice_demo

import shlex
import sys
import logging
import shutil
from pathlib import Path

ENC = "utf-8"


def check_call(args, ignore_return_code=False):
    import subprocess

    cmd_str = " ".join(args)
    print(f"Execute command: '{cmd_str}'")
    p = subprocess.Popen(
        args,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding=ENC,
    )
    stdout, stderr = p.communicate()
    if stdout:
        # logging.debug(stdout)
        print(f"stdout: {stdout}")
    if stderr:
        # logging.debug(stderr)
        print(f"stderr: {stderr}")
    if not ignore_return_code and p.returncode != 0:
        raise RuntimeError(f"failed to run '{cmd_str}'")
    return stdout


class MiDevice:
    def __init__(self, uid: str, base_path: Path, alias: str, exclude=None):

        self.uid: str = uid
        self.alias: str = alias
        if exclude is None:
            exclude = []
        self.exclude = exclude
        # computed properties
        self.target: Path = base_path.joinpath(self.alias).resolve()
        self._mount_point: Path = base_path.joinpath(".mount").joinpath(self.uid).resolve()

        self.is_mounted: bool = False
        self.is_present: bool = self._is_present()

    def _is_present(self):
        try:
            devices = check_call(["idevice_id", "-l"])
            return self.uid in devices
        except RuntimeError as e:
            print(f"error while checking for devices {e}")
        return False

    def mount(self):
        if not self.is_present:
            return

        try:
            self._mount_point.mkdir(parents=True, exist_ok=True)
            cmd = ["ifuse", "-u", shlex.quote(self.uid), str(self._mount_point)]
            check_call(cmd)
            self.is_mounted = True
        except RuntimeError as e:
            print(f"Error while mounting: {e}")

    def umount(self):
        if not self.is_mounted:
            return

        try:
            cmd = ["umount", str(self._mount_point)]
            check_call(cmd)
            self.is_mounted = False
        except RuntimeError as e:
            print(f"Error while unmounting {self._mount_point}, with {e}")
            print("Do not unplug the iOS device while Backup is running")
            print("try running:")
            print(f"    sudo umount --force {self._mount_point}")

    def backup(self):
        if not self.is_mounted:
            print(f"cannot backup {self.alias}: device not mounted")
            return

        try:
            if not self.target.exists():
                self.target.mkdir(parents=True, exist_ok=True)
            else:
                # set last modifcation time to the begin of backup time
                self.target.touch()

            cmd = ["rsync", "-avzh"]
            for e in self.exclude:
                cmd.extend(["--exclude", e])
            cmd.extend([str(self._mount_point), str(self.target)])
            check_call(cmd)

        except RuntimeError as e:
            print(f"error while backup of {self.alias}: {e}")
            logging.error(e)

    def prune_photos(self):
        if not self.is_mounted:
            print(f"cannot prune {self.alias}: device not mounted")
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
            devices = check_call(["idevicepair", "list"])
            return self.uid in devices
        except RuntimeError as e:
            print(f"Error while checking if {self.uid} is paired with this host: {e}")
        return False

    def pair(self):
        try:
            # have to wait for user interaction.
            cmd = ["idevicepair", "-u", self.uid, "pair"]
            check_call(cmd)
        except RuntimeError as e:
            print(e)

    @classmethod
    def discover(cls):
        return check_call(["idevice_id", "-l"])

    def __del__(self):
        self.umount()

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.umount()


def main(argv):
    import argparse
    import configparser

    parser = argparse.ArgumentParser(
        description="this is the Dickstiel iOS Backup tool! Regularly backup multiple iOS devices",
    )

    parser.add_argument(
        "--explain",
        help="Explain what %(prog)s does (and stop)",
        action="store_true",
    )

    parser.add_argument(
        "--config",
        "-c",
        metavar="FILE",
        dest="config",
        required=True,
        help="use config file",
    )

    parser.add_argument(
        "--discover",
        "-d",
        dest="discover",
        help="list devices that are currently connected, yet not in your config file.",
    )

    parser.add_argument("--verbose", "-v", help="verbose output", action="count")

    # safety net if no arguments are given call for help
    if len(sys.argv[1:]) == 0:
        parser.print_help()
        return 0

    pa = parser.parse_args(argv[1:])

    if pa.explain:
        sys.stdout.write(__doc__)
        return 0

    # Check for prereq
    required_commands = ["idevicepair", "ifuse", "rsync", "umount", "idevice_id"]
    for cmd in required_commands:
        satisfied = True
        if shutil.which(cmd) is None:
            print(f"cmd: {cmd} is missing")
            satisfied = False

        if not satisfied:
            print(f"Requirements are missing! please install")
            print(f"    apt install libimobiledevice ")
            return 1

    if pa.config:

        config = configparser.ConfigParser()
        config.read(pa.config)

        if pa.discover:
            for dev in MiDevice.discover():
                if not config.has_section(dev):
                    print(f"device discovered: {dev}")
                    print(f"Add to your config file:")
                    print()
                    print("---")
                    print(f"[{dev}]")
                    print(f"name = {dev}")
                    print("---")
                    print()
                    print(f"Also pair your device by executing:")
                    print(f"    idevicepair -u {dev}")

        for s in config.sections():

            name = config.get(s, "name")
            if name is None:
                print(f"name is missing from config section: {s}")
                continue

            if config.getboolean(s, "ignore", fallback=False):
                print(f"ignoring device {name} with uid: {s}")
                continue

            backup_path = config.get(s, "backup_path")
            if backup_path is None:
                print(f"backup_path is missing from config section {s} or in [DEFAULT] section")
                continue
            backup_path = Path(backup_path)

            exclude = config.get(s, "exclude")
            if exclude is not None:
                if exclude.startswith("[") and exclude.endswith("]"):
                    import json

                    try:
                        exclude = json.loads(exclude)
                    except RuntimeError as e:
                        print(
                            f"error reading exclude array from config section {s}, error={e}"
                        )
                        print(f"stopping backup for device {name} with uid {s} ")
                        continue
                else:
                    # only single to exclude
                    exclude = [exclude]

            device = MiDevice(uid=s, base_path=backup_path, alias=name, exclude=exclude)

            if not device.is_present:
                print(f"device {name} with uid {s} not here, skipping")
                continue

            if not device.check_paired():
                print(f"please pair your device {device.alias} uid={device.uid} by executing:")
                print(f"    idevicepair -u {device.uid}")
                continue

            device.mount()
            device.backup()

            if config.getboolean(s, "prune_photos", fallback=False):
                device.prune_photos()

            device.umount()
            device.notify()

    return 0


if "__main__" == __name__:
    sys.exit(main(sys.argv))
