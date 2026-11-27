#!/usr/bin/env python3
"""Check a list against the rules the apps apply. Exit status 1 and a line per problem if it breaks any."""
import sys

import speakers_lib as lib

if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else "speakers.json"
    problems = lib.validate(lib.load(path))
    for p in problems:
        print(p)
    sys.exit(1 if problems else 0)
