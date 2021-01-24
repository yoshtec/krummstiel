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

# important keys
TOP = "$top"
OBJ = "$objects"
TIT = 'title'
ASSETS = 'assetUUIDs'
SUUID = "uuid"
TRASH = 'isInTrash'

PLISTHEADER = b'bplist00'

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

        self._uuid_index = self.metadata[TOP][SUUID].data
        self.uuid = uuid.UUID("{" + self.metadata[OBJ][self._uuid_index] + "}")

        for t in self.metadata[TOP]:
            index = self.metadata[TOP][t]

            if isinstance(index, plistlib.UID):
                index = index.data
                data = self.metadata[OBJ][index]
                print(f"t {t}, type {type(data)}")
                if type(data) is bytes:
                    if len(data) > len(PLISTHEADER) and data[0:len(PLISTHEADER)] == PLISTHEADER:
                        data2 = plistlib.loads(data)  # seems recursive a
                        data = data2
                    elif str(t).endswith('UUIDs'):
                        data2 = data
                        data = []
                        i = 0
                        while i < len(data2):
                            ux = uuid.UUID(bytes=data2[i:i + 16])
                            data.append(ux)
                            i = i + 16

                self.unpacked_metadata[t] = data

            else:
                self.unpacked_metadata[t] = index

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
        pm = PhotosMetadataFile(a)
        print(f"file {a}, name: {pm.get_name()}, uuids:{pm.asset_uuids}")
        pm.dumpex()

    for a in p.glob("*.memorymetadata"):
        print(f"file {a}")
        pm = BaseMetadataFile(a)
        print(f"file {a}, name: {pm.uuid}")
        pm.dumpex()


if __name__ == '__main__':
    readfiles()
