#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# SPDX-License-Identifier: MIT

"""
handle Metadata information from ios

For documentation visit: https://github.com/yoshtec/krummstiel
"""

from pathlib import Path
import uuid
import pprint
import click
import plistlib
import datetime

# important keys
TOP = "$top"
OBJ = "$objects"
ARC = '$archiver'

TIT = 'title'
ASSETS = 'assetUUIDs'
SUUID = "uuid"
TRASH = 'isInTrash'

NSKEYS = 'NS.objects'
NSOBJECTS = 'NS.objects'
NSTIME = 'NS.time'
NSDATA = "NS.data"

PLISTHEADER = b'bplist00'


def _unwrap_bytes(b, uuids=False):
    if len(b) > len(PLISTHEADER) and b[0:len(PLISTHEADER)] == PLISTHEADER:
        return unwrap(plistlib.loads(b))

    if uuids:
        return _unwrap_uuids(b)

    return b


def _unwrap_uuids(b):
    data = []
    i = 0
    while i < len(b):
        ux = uuid.UUID(bytes=b[i:i + 16])
        data.append(ux)
        i = i + 16
    return data


def unwrap_dict(d: dict):
    if not d:
        return {}

    if NSKEYS in d and NSOBJECTS in d:
        data2 = {}
        for k, v in zip(d[NSKEYS], d[NSOBJECTS]):
            data2[unwrap(k)] = unwrap(v)
        return data2

    if NSOBJECTS in d:
        data2 = []
        for v in d[NSOBJECTS]:
            data2.append(unwrap(v))
        return data2

    if ARC in d and TOP in d and OBJ in d:
        if d[ARC] == 'NSKeyedArchiver':
            return read_nsarchiver(d)

    if NSTIME in d:
        return datetime.datetime(2001, 1, 1) + datetime.timedelta(seconds=d[NSTIME])

    for t in d:
        d[t] = unwrap(d[t])

    return d


def unwrap(x):
    if not x:
        return ""

    if isinstance(x, int) or isinstance(x, float):
        return x

    if isinstance(x, plistlib.UID):
        return x.data

    if type(x) is dict:
        return unwrap_dict(x)

    if type(x) is bytes:
        return _unwrap_bytes(x)

    return x


def read_nsarchiver(plist=None):

    if not plist:
        return {}

    # need all 3 items in the dict
    if ARC not in plist or TOP not in plist or OBJ not in plist:
        return plist

    if plist[ARC] != 'NSKeyedArchiver':
        return plist

    result_dict = {}
    for t in plist[TOP]:
        index = plist[TOP][t]

        if isinstance(index, plistlib.UID):
            index = index.data
            data = plist[OBJ][index]
            print(f"t {t}, type {type(data)}")

            if type(data) is bytes:
                result_dict[t] = _unwrap_bytes(data, str(t).endswith('UUIDs'))
            else:
                result_dict[t] = unwrap(data)
        else:
            result_dict[t] = index

    return result_dict


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

        self.unpacked_metadata = read_nsarchiver(self.metadata)

    def dump(self):
        pprint.pp(self.metadata)

    def dumpex(self):
        pprint.pp(self.unpacked_metadata)


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
            ux = uuid.UUID(bytes=assets_data[i:i + 16])
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
@click.option("--path", type=click.Path(exists=True, file_okay=False))
def readfiles(path=None):

    print("hi")
    p = Path(path)

    for a in p.glob("*.albummetadata"):
        print(f"file {a}")
        pm = BaseMetadataFile(a)
        #print(f"file {a}, name: {pm.get_name()}, uuids:{pm.asset_uuids}")
        pm.dumpex()

    for a in p.glob("*.memorymetadata"):
        print(f"file {a}")
        pm = BaseMetadataFile(a)
        #print(f"file {a}, name: {pm.uuid}")
        pm.dumpex()


if __name__ == '__main__':
    readfiles()
