#!/usr/bin/env bash
# SPDX-License-Identifier: MIT

if ./krummstiel/krummstiel.py -vv --config example.ini ; then
  exit 1
else
  exit 0
fi