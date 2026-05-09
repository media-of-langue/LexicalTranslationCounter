"""Helpers for wordlist CSV files."""

import csv
import re


INTEGER_RE = re.compile(r"[-+]?\d+")


def read_wordlist(path):
    with open(path, mode="r") as inp:
        reader = list(csv.reader(inp))
    if reader and not INTEGER_RE.fullmatch(reader[0][0]):
        reader = reader[1:]
    return {rows[1]: int(rows[0]) for rows in reader if len(rows) >= 2}


def write_wordlist(path, wordlist):
    with open(path, "w") as f:
        writer = csv.writer(f)
        for key, word_id in wordlist.items():
            writer.writerow([word_id, key, "f"])
