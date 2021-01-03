# Information on Photos.sqlite

`Photos.sqlite` is an sqlite database in the `PhotoData`

Some general information https://www.forensicmike1.com/2019/05/02/ios-photos-sqlite-forensics/

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