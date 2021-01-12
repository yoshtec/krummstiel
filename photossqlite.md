# Information on Photos.sqlite

`Photos.sqlite` is an sqlite database conatining Metadata of all Pictures in the Library from your iPhone, iPad and macOS Photos Libraries.

Since it is not generally documented, I will document my research in understanding the Database here.


Location:
* macOS `/Users/USERID/Pictures/Photos Library.photoslibrary/database/Photos.sqlite` hidden from Finder in the Photos Library.
* iPhone & iPad: `PhotoData/Photos.sqlite` Folder on the mounted device. Photos itself are stored in `DCIM/****APPL`.


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
