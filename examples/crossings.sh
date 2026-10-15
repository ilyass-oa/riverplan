#!/bin/sh
set -eu
riverplan 1 2 5 10 --capacity 2
riverplan 1 3 6 8 --capacity 2 --deadline 18 --json
