# Information on Photos.sqlite

`Photos.sqlite` is an sqlite database containing Metadata of all Pictures in the Library from your iPhone and iPad. 
The database is stored in `PhotoData/Photos.sqlite` on the mounted device. 
Photos itself are stored in `DCIM/****APPL`. Not all Metadata is stored in the Database itself, a lot of important
information is scattered within subdirectories of `PhotoData` stored in horrible plistfiles.

Since it is not generally documented, I will document my research in understanding the Database here. 

MacOS also has a similar sqlite File hidden from Finder access stored within the Photos Library 
at `/Users/USERID/Pictures/Photos Library.photoslibrary/database/Photos.sqlite`. Although it sounds similar, it is for
the most part totally different. Please check  the [osxphotos](https://github.com/RhetTbull/osxphotos) lib for accessing 


Ways of analysing, store or snapshot different versions and just do an diff of the Files

```
sqldiff Older-Photos.sqlite Newer-Photos.sqlite
```

# Questions

## Where are is the Relation of Photos to Albums? E.g. which Photo is in Album 'A'
Tried to do an sqldiff, but unfortunately no clear Pic where it is. Came to the conclusion that it might be stored in other files `PhotoData/AlbumsMetadata` is a good candidate.
 
Analyse via 
```sh
plistutil -i SOME-UUID.albummetadata
plistutil -i SOME-UUID.albummetadata | xmllint --xpath '//dict/array/string' -    

# data field seems interesting
for i in *.albummetadata; do plistutil -i "$i" | xmllint --xpath "translate(normalize-space(//dict/array/data/text()), ' &#9;&#10;&#13', '')" -  ; done
```

Python snippet for extracting Picture UUIDs . Link to file can be found then in `ZASSET` Table in field `ZUUID`
```python

import plistlib
import uuid
import pprint

p = 6 # 6 for .albummetadata, 8 for .memorymetadata
f = open("F6E73B17-FFB3-4718-801A-2E70B56AEB9A.albummetadata", "rb")
x = plistlib.load(f)
pprint.pp(x)

chunk_size= 4
for i in range(0, len(x['$objects'][p]), chunk_size):
    ux = uuid.UUID(bytes=x['$objects'][p][i:i+16])
    print(ux)
    
```


# Tables

## ZASSET
Table with interesting fields `ZDIRECTORY` and `ZFILENAME` for Filenames mapped to the `ZUUID` which is referenced in 
other tables   

Finding more information on all Tables that directly reference `ZASSET`:
```sqlite
SELECT DISTINCT m.name as 'tablename',  ti.* 
  FROM sqlite_master AS m,
       pragma_table_info(m.name) AS ti
 WHERE m.type='table' and ti.name like 'ZASSET%'
 ORDER BY 1,3;
```

## ZGENERICALBUM
Contains the Albums and 
* `ZTITLE` Title of the Album
* `ZKIND` if it was manually created then this is 2 otherwise some number
* `ZKEYASSET` Picture which is in the Preview from `ZASSET`




# Other Sources:
* Some general information from a forensics guy <https://www.forensicmike1.com/2019/05/02/ios-photos-sqlite-forensics/>

* A Rust library for interaction with the Database: <https://github.com/dangreco/rust-apple-photos>
