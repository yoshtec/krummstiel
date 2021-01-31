#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# SPDX-License-Identifier: MIT

"""
handle Metadata information from ios.
Reads and unwraps all kind of plist in use for albums e.g.
 *.facemetadata, *.albummetadata, *.foldermetadata

For documentation visit: https://github.com/yoshtec/krummstiel
"""

from pathlib import Path
import uuid
import pprint
import click
import plistlib
from plistlib import InvalidFileException
import datetime
import shutil
import sys
import re

UUID_REGEX = re.compile(
    "[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}\Z", re.I
)

# important keys
TOP = "$top"
OBJ = "$objects"
ARC = "$archiver"
CLASS = "$class"

TIT = "title"
ASSETS = "assetUUIDs"
SUUID = "uuid"
TRASH = "isInTrash"
ASSETUUIDS = "assetUUIDs"
ROOT = "root"

PHMFEATUREENCODER = "PHMemoryFeatureEncoder"
NSKEYEDARCHIVER = "NSKeyedArchiver"

NSKEYS = "NS.keys"
NSOBJECTS = "NS.objects"
NSTIME = "NS.time"
NSDATA = "NS.data"
NSSTRING = "NS.string"

PLISTHEADER = b"bplist00"


def _unwrap_bytes(b, uuids=False):
    if len(b) > len(PLISTHEADER) and b[0 : len(PLISTHEADER)] == PLISTHEADER:
        return unwrap(plistlib.loads(b))

    if uuids:
        return _unwrap_uuids(b)

    return b


def _unwrap_uuids(b):
    data = []
    i = 0
    while i < len(b):
        ux = uuid.UUID(bytes=b[i : i + 16])
        data.append(ux)
        i = i + 16
    return data


def _unwrap_dict(d: dict, orig: list = None):
    if d is None:
        return {}

    if NSSTRING in d:
        return d[NSSTRING]

    if NSTIME in d:
        return datetime.datetime(2001, 1, 1) + datetime.timedelta(seconds=d[NSTIME])

    if ARC in d and TOP in d and OBJ in d:
        if d[ARC] in [NSKEYEDARCHIVER, PHMFEATUREENCODER]:
            result_dict: dict = {}
            for t in d[TOP]:
                index = d[TOP][t]

                if isinstance(index, plistlib.UID):
                    index = index.data
                    data = d[OBJ][index]
                    if type(data) is bytes:
                        result_dict[t] = _unwrap_bytes(data, str(t).endswith("UUIDs"))
                    else:
                        result_dict[t] = unwrap(data, d[OBJ])
                else:
                    result_dict[t] = index

            # unpack single "root" dictionaries
            if ROOT in result_dict and len(result_dict) == 1:
                return result_dict[ROOT]

            return result_dict

    if NSDATA in d:
        return unwrap(d[NSDATA])

    if NSKEYS in d and NSOBJECTS in d:
        data2 = {}
        for k, v in zip(d[NSKEYS], d[NSOBJECTS]):
            # print(f"k,v:{k},{v}")
            k = unwrap(k, orig)
            v = unwrap(v, orig)
            # print(f"k,v:{k},{v}")
            data2[k] = v
        return data2

    if NSOBJECTS in d:
        data2 = []
        for v in d[NSOBJECTS]:
            data2.append(unwrap(v, orig))
        return data2

    for t in d:
        d[t] = unwrap(d[t], orig)

    return d


def _unwrap_list(l: list, orig: list = None):
    if not l:
        return []

    result_list = []
    for e in l:
        result_list.append(unwrap(e, orig))
    return result_list


def unwrap(x, orig: list = None):
    if x is None:
        return ""

    if isinstance(x, int) or isinstance(x, float) or isinstance(x, bool):
        return x

    if isinstance(x, plistlib.UID):
        x = x.data
        if orig is not None and len(orig) > x:
            x = unwrap(orig[x], orig)
        return x

    if isinstance(x, str):
        if UUID_REGEX.match(x):
            return uuid.UUID(x)
        return x

    if isinstance(x, dict):
        return _unwrap_dict(x, orig)

    if isinstance(x, list):
        _unwrap_list(x, orig)

    if type(x) is bytes:
        return _unwrap_bytes(x)

    # Fallback just return the original
    return x


def read_ns_archiver(plist=None):
    return unwrap(plist)


def read_plist(plist=None):

    if not plist:
        return {}

    return unwrap(plist)


class BaseMetadataFile:
    def __init__(self, file: Path):
        self.file = file
        self.metadata = {}
        self.unpacked_metadata = {}

        self._read()

    def _read(self):
        import plistlib

        if not self.file.is_file():
            raise RuntimeError(f"Path '{self.file}' is not a regular file)")

        with open(self.file, "rb") as f:
            self.metadata = plistlib.load(f)

        self.unpacked_metadata = unwrap(self.metadata)

    def dump(self):
        width, lines = shutil.get_terminal_size()
        pprint.pp(self.metadata, width=width)

    def dumpex(self):
        width, lines = shutil.get_terminal_size()
        pprint.pp(self.unpacked_metadata, width=width)


class PhotosMetadataFile(BaseMetadataFile):
    def __init__(self, file: Path):
        BaseMetadataFile.__init__(self, file=file)

        self.asset_uuids = []
        self.title = ""
        self.uuid = None

        self.isInTrash = False

        self._read()

        if SUUID in self.unpacked_metadata:
            self.uuid = self.unpacked_metadata[SUUID]

        if TIT in self.unpacked_metadata:
            self.title = self.unpacked_metadata[TIT]

        if ASSETUUIDS in self.unpacked_metadata:
            self.asset_uuids = self.unpacked_metadata[ASSETUUIDS]

    def get_picture_uuids(self):
        return self.asset_uuids


class MemoryMetaDataFile(PhotosMetadataFile):
    def __init__(self, file: Path):
        PhotosMetadataFile.__init__(self, file)


@click.command()
@click.argument(
    "file", nargs=-1, type=click.Path(exists=True, file_okay=True, readable=True)
)
@click.option("--raw", "-r", default=False, is_flag=True)
def cat(file=None, raw=False):
    sys.exit(cat_metadata_files(file, raw))


def cat_metadata_files(file=None, raw=False, recurse=False):
    stack: list = []
    if not file:
        return 0

    stack.extend(file)

    while len(stack) > 0:
        p = Path(stack.pop())
        if p.is_dir():
            if recurse:
                stack.extend(p.iterdir())
        elif p.is_file():
            click.secho(f"Analyzing file {p}:", bold=True)
            try:
                pm = BaseMetadataFile(p)
                if raw:
                    pm.dump()
                    click.echo("")
                pm.dumpex()
            except InvalidFileException as i:
                click.echo(f" - is not a valid plist. Skipping over Error '{i}'.")
            click.echo("")
    return 0


if __name__ == "__main__":
    cat()
