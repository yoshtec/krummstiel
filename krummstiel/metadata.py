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
import sqlite3
import re

UUID_REGEX = re.compile(
    "[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}\Z", re.I
)

PATH_PICTURES = Path("DCIM")
PATH_PHOTO_METADATA = Path("PhotoData")
PATH_FACES = PATH_PHOTO_METADATA / Path("FacesMetadata")
PATH_ALBUMS = PATH_PHOTO_METADATA / Path("AlbumsMetadata")

# important keys
NS_TOP = "$top"
NS_OBJ = "$objects"
NS_ARC = "$archiver"
NS_CLASS = "$class"

NS_KEYS = "NS.keys"
NS_OBJECTS = "NS.objects"
NS_TIME = "NS.time"
NS_DATA = "NS.data"
NS_STRING = "NS.string"

KEY_TITLE = "title"
KEY_ASSETS = "assetUUIDs"
KEY_UUID = "uuid"
KEY_TRASH = "isInTrash"
KEY_ASSETUUIDS = "assetUUIDs"
KEY_ROOT = "root"

TYPE_PHMFEATUREENCODER = "PHMemoryFeatureEncoder"
TYPE_NSKEYEDARCHIVER = "NSKeyedArchiver"

PLISTHEADER = b"bplist00"


def _is_plist(b: bytes):
    return len(b) > len(PLISTHEADER) and b[0 : len(PLISTHEADER)] == PLISTHEADER


def _unwrap_bytes(b, uuids=False):
    if _is_plist(b):
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

    if NS_STRING in d:
        return d[NS_STRING]

    if NS_TIME in d:
        return datetime.datetime(2001, 1, 1) + datetime.timedelta(seconds=d[NS_TIME])

    if NS_ARC in d and NS_TOP in d and NS_OBJ in d:
        if d[NS_ARC] in [TYPE_NSKEYEDARCHIVER, TYPE_PHMFEATUREENCODER]:
            result_dict: dict = {}
            for t in d[NS_TOP]:
                index = d[NS_TOP][t]

                if isinstance(index, plistlib.UID):
                    index = index.data
                    data = d[NS_OBJ][index]
                    if type(data) is bytes:
                        result_dict[t] = _unwrap_bytes(data, str(t).endswith("UUIDs"))
                    else:
                        result_dict[t] = unwrap(data, d[NS_OBJ])
                else:
                    result_dict[t] = index

            # unpack single "root" dictionaries
            if KEY_ROOT in result_dict and len(result_dict) == 1:
                return result_dict[KEY_ROOT]

            return result_dict

    if NS_DATA in d:
        return unwrap(d[NS_DATA])

    if NS_KEYS in d and NS_OBJECTS in d:
        data2 = {}
        for k, v in zip(d[NS_KEYS], d[NS_OBJECTS]):
            # print(f"k,v:{k},{v}")
            k = unwrap(k, orig)
            v = unwrap(v, orig)
            # print(f"k,v:{k},{v}")
            data2[k] = v
        return data2

    if NS_OBJECTS in d:
        data2 = []
        for v in d[NS_OBJECTS]:
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
    def __init__(self, file: Path = None, bytes: bytes = None):
        self.file = file
        self.raw_metadata = {}
        self.metadata = {}

        if file:
            if not self.file.is_file():
                raise RuntimeError(f"Path '{self.file}' is not a regular file)")

            with open(self.file, "rb") as f:
                self.raw_metadata = plistlib.load(f)

        elif bytes and _is_plist(bytes):
            self.raw_metadata = plistlib.loads(bytes)
        else:
            raise RuntimeError(f"Supplied file '{file}' is invalid and supplied bytes is not a plist")

        self.metadata = unwrap(self.raw_metadata)

    def dump_raw(self):
        width, lines = shutil.get_terminal_size()
        pprint.pp(self.raw_metadata, width=width)

    def dump(self):
        width, lines = shutil.get_terminal_size()
        pprint.pp(self.metadata, width=width)


class PhotosMetadataFile(BaseMetadataFile):
    def __init__(self, file: Path):
        BaseMetadataFile.__init__(self, file=file)

        self.asset_uuids = []
        self.title = ""
        self.uuid = None
        self.isInTrash = False

        if KEY_UUID in self.metadata:
            self.uuid = self.metadata[KEY_UUID]

        if KEY_TITLE in self.metadata:
            self.title = self.metadata[KEY_TITLE]

        if KEY_ASSETUUIDS in self.metadata:
            self.asset_uuids = self.metadata[KEY_ASSETUUIDS]

        if KEY_TRASH in self.metadata:
            self.isInTrash = bool(self.metadata[KEY_TRASH])

    def get_picture_uuids(self):
        return self.asset_uuids


class IOSPhotosDB:

    def __init__(self, database_file: Path):
        if not database_file:
            raise RuntimeError("database file is empty")
        database_file = Path(database_file)
        if not database_file.exists():
            raise RuntimeError("Database file does not exist")
        if not database_file.is_file():
            raise RuntimeError("Database file is not a regular file")

        self.database_uri = f"file:{database_file.resolve()}?mode=ro"
        self._db = sqlite3.connect(self.database_uri, uri=True)
        self._connected = True

    def get_picture_files(self, uuid_list: list):
        """

        :param uuid_list: list of uuids
        :return: a dictionary with key uuid and value filename of picture
        """
        if not uuid_list or len(uuid_list) == 0:
            return {}

        q_str = ",".join("?" * len(uuid_list))

        sql = f"select a.ZUUID, a.ZDIRECTORY, a.ZFILENAME from ZASSET a where a.ZUUID in ({q_str})"

        result_rows = self._db.execute(sql, [str(u).upper() for u in uuid_list])
        result = {}
        for row in result_rows.fetchall():
            result[row[0]] = Path(row[1]) / Path(row[2])
        return result

    def get_stats(self):
        """get some statistics from the Photos.sqlite"""
        pass

    def list_all_albums(self):
        pass

    def list_faces(self):
        pass

    def list_memories(self):
        pass

    def list_albums(self):
        sql = f"SELECT ZUUID, ZTITLE FROM ZGENERICALBUM"
        result = {}
        for row in self._db.execute(sql).fetchall():
            result[row[0]] = row[1]
        return result


def cat_metadata_files(file=None, raw=False, recurse=False):
    stack: list = []
    if not file:
        return 0

    stack.extend(file)

    while len(stack) > 0:
        p = Path(stack.pop())
        if p.is_dir() and recurse:
            stack.extend(p.iterdir())
        elif p.is_file():
            click.secho(f"Analyzing file {p}:", bold=True)
            try:
                pm = BaseMetadataFile(p)
                if raw:
                    pm.dump_raw()
                    click.echo("")
                pm.dump()
            except InvalidFileException as i:
                click.echo(f" - is not a valid plist. Skipping over Error '{i}'.")
            click.echo("")
    return 0


def list_albums(db_file):
    db_file = Path(db_file)
    db = IOSPhotosDB(db_file)
    base_path = db_file.parents[0] / Path("AlbumsMetadata")
    albums: dict = db.list_albums()
    for k, v in albums.items():
        files = base_path.glob(f"{k}.*")
        had_file = False
        pprint.pp(f"Album uid={k}, name={v}")
        for f in files:
            pprint.pp(f)
            bmf = PhotosMetadataFile(f)
            bmf.dump()
            pcitures = db.get_picture_files(bmf.get_picture_uuids())
            pprint.pp(pcitures)
            had_file = True
        if not had_file:
            pprint.pp(f"no file for Album: uid={k} name={v} ")
