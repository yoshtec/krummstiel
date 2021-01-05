# Information on Photos.sqlite

`Photos.sqlite` is an sqlite database in the `PhotoData`. I contains a lot of Metadata for your Photos on the iPhone /
iPad. 

Since it is not generally documented, I will document my research in understanding the Database here.


# Tables

## ZASSET
Table with interesting fields `ZDIRECTORY` and `ZFILENAME` for Filenames mapped to the `ZUUID` which is referenced in 
other tables   


Finding mor information on all Tables that directly reference `ZASSET`:
```sqlite
SELECT DISTINCT m.name as 'tablename',  ti.* 
  FROM sqlite_master AS m,
       pragma_table_info(m.name) AS ti
 WHERE m.type='table' and ti.name like 'ZASSET%'
 ORDER BY 1,3;
```

# Other Sources:
* Some general information from a forensics guy <https://www.forensicmike1.com/2019/05/02/ios-photos-sqlite-forensics/>

* A Rust library for interaction with the Database: <https://github.com/dangreco/rust-apple-photos>