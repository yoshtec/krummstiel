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
import datetime
import shutil
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
            result_dict = {}
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

    if type(x) is bytes:
        return _unwrap_bytes(x)

    # Fallback just return the original
    return x


def read_ns_archiver(plist=None):

    if not plist:
        return {}

    # need all 3 items in the dict
    if ARC not in plist or TOP not in plist or OBJ not in plist:
        return plist

    if plist[ARC] not in [NSKEYEDARCHIVER, PHMFEATUREENCODER]:
        return plist

    return unwrap(plist)


class BaseMetadataFile:
    def __init__(self, file: Path):
        self.metadata = None
        self.file = file
        self.uuid = None
        self.unpacked_metadata = {}

        self._read()

    def _read(self):
        import plistlib

        if not self.file.is_file():
            raise RuntimeError(f"Path '{self.file}' is not a regular file)")

        with open(self.file, "rb") as f:
            self.metadata = plistlib.load(f)

        self.unpacked_metadata = read_ns_archiver(self.metadata)

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

        # sensible defaults
        self._asset_uuid_index = 6
        self._title_index = 0
        self._uuid_index = 2

        self.isInTrash = False

        self._read()

    def _read(self):

        BaseMetadataFile._read(self)

        if TIT in self.metadata[TOP]:
            self._title_index = self.metadata[TOP][TIT].data  # UID type
        else:
            self._title_index = self._uuid_index

        self._asset_uuid_index = self.metadata[TOP][ASSETS].data  # UID type

        self.asset_uuids = []
        assets_data = self._get_data()

        i = 0
        while i < len(assets_data):
            ux = uuid.UUID(bytes=assets_data[i : i + 16])
            self.asset_uuids.append(ux)
            i = i + 16

    def _get_data(self):
        if self.metadata:
            return self.metadata[OBJ][self._asset_uuid_index]
        return []

    def get_name(self):
        if self.metadata:
            return self.metadata[OBJ][self._title_index]

    def get_picture_uuids(self):
        return self.asset_uuids


class MemoryMetaDataFile(PhotosMetadataFile):
    def __init__(self, file: Path):
        PhotosMetadataFile.__init__(self, file)


#    def get_name(self):
#        if self.metadata:
#            return f"{self.metadata[OBJ][2]} {self.metadata[OBJ][3]}"


@click.command()
@click.argument(
    "file", nargs=-1, type=click.Path(exists=True, file_okay=True, readable=True)
)
@click.option("--raw", "-r", default=False, is_flag=True)
def cat(file=None, raw=False):

    for p in file:
        p = Path(p)
        print(f"Analyzing file {p}:")
        pm = BaseMetadataFile(p)
        if raw:
            pm.dump()
        pm.dumpex()


if __name__ == "__main__":
    cat()
