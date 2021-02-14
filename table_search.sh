#!/usr/bin/env bash
# brute force list grep through an sqlite database try to find content
for o in $(sqlite-utils tables $1 --csv --no-headers)
do
  echo $o
  sqlite-utils $1 "select * from $o" --csv | grep -i $2
done