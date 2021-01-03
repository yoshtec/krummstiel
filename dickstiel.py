#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# SPDX-License-Identifier: MIT

"""

"""

# TODO: evaluate and use python bindings of libimobiledevice https://github.com/upbit/python-imobiledevice_demo


import os
import sys
import logging
import shlex
import shutil
from pathlib import Path

ENC = "utf-8"


def check_call(args, ignore_return_code=False):
    import subprocess

    cmd_str = " ".join(args)
    logging.info(f"Execute command: '{cmd_str}'")
    p = subprocess.Popen(
        args,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding=ENC,
    )
    stdout, stderr = p.communicate()
    if stdout:
        logging.debug(stdout)
    if stderr:
        logging.debug(stderr)
    if not ignore_return_code and p.returncode != 0:
        raise RuntimeError(f"failed to run '{cmd_str}'")
    return stdout


class MiDevice:
    def __init__(self, uid: str, base_path: Path, alias: str, exclude=None):

        if exclude is None:
            exclude = []
        self.exclude = exclude
        self.uid = uid
        self.alias = alias
        self.target: Path = base_path.joinpath(self.alias)
        self._mount_point = Path(self.target).joinpath(".mount").joinpath(self.uid)
        self.is_mounted = False
        self.is_present: bool = self._is_present()

    def _is_present(self):
        try:
            devices = check_call(["idevice_id", "-l"])
            return self.uid in devices
        except RuntimeError as e:
            print(f"error while checking for devices {e}")
        return False

    def mount(self):
        try:
            self._mount_point.mkdir(parents=True, exist_ok=True)
            cmd = ["ifuse", "-u", self.uid, self._mount_point]
            check_call(cmd)
            self.is_mounted = True
        except RuntimeError as e:
            print(f"Error while mounting: {e}")

    def umount(self):
        if not self.is_mounted:
            return

        try:
            cmd = ["umount", self._mount_point]
            check_call(cmd)
            self.is_mounted = False
        except RuntimeError as e:
            print(f"Error while unmounting {self._mount_point}, with {e}")
            print("Do not unplug the iOS device while Backup is running")
            print("try running:")
            print(f"    sudo umount --force {self._mount_point}")

    def backup(self):
        try:
            cmd = ["rsync", "-avzh"]
            for e in self.exclude:
                cmd.extend("--exclude")
                cmd.extend(e)
            cmd.extend([self._mount_point, self.target])
            check_call(cmd)
        except RuntimeError as e:
            logging.error(e)

    def prune_photos(self):
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
        cmd = ["idevice_id", "-l"]
        devices = check_call(cmd)

    def __del__(self):
        self.umount()

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.umount()


def main(argv):
    import argparse

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
            print(f"prereqs are missing! please install")
            print(f"    apt install libimobiledevice")
            return 1

    if pa.config:
        import configparser

        config = configparser.ConfigParser()
        config.read(pa.config)

        for s in config.sections():

            print("section:", s)
            for a in config[s]:
                print("config", a, config[s][a])

            uid = config.get(s, "uid")
            backup_path = Path(config.get(s, "backup_path"))

            if backup_path is None:
                print(f"backup_path is missing from config section {s}")
                continue
            elif uid is None:
                print(f"uid is missing from config section: {s}")
                continue

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
                        print(f"stopping backup for device {s} with uid {uid} ")
                        continue
                else:
                    # only single to exclude
                    exclude = [exclude]

            device = MiDevice(uid=uid, base_path=backup_path, alias=s, exclude=exclude)

            device.mount()
            device.backup()

            if config.getboolean(s, "prune_photos", fallback=False):
                device.prune_photos()

            device.umount()
            device.notify()

    return 0


if "__main__" == __name__:
    sys.exit(main(sys.argv))
