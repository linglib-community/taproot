#!/usr/bin/env python3
"""What the map knows about linglib that the import graph does not say.

* The family of each language directory, from the WALS language table in the checkout
  (`Linglib/Data/WALS/raw/languages.csv`), where the directory is named as a WALS language or genus
  is, so that the hundred-odd language directories are drawn by family. A directory with no such
  match is left ungrouped; nothing is guessed.
* Where the theory areas sit on the top-level map, as `[column, row]`: the levels of grammar in
  their usual order, logic beneath semantics, processing to the side. A choice about the picture,
  not a measurement; the arrows on the map show what imports what.

    python3 lib/groups.py [CHECKOUT]     # print the table
"""
import collections, csv, json, os, re, sys

LAYOUT = {'': {'Phonology': [0, 0], 'Morphology': [1, 0], 'Syntax': [2, 0], 'Semantics': [3, 0],
               'Pragmatics': [4, 0], 'Discourse': [5, 0], 'Processing': [1, 1], 'Logic': [3, 1]}}


def families(root):
    langs, wals = os.path.join(root, 'Linglib/Languages'), os.path.join(root, 'Linglib/Data/WALS/raw/languages.csv')
    if not (os.path.isdir(langs) and os.path.exists(wals)): return {}
    norm = lambda s: re.sub(r'[^a-z]', '', s.lower())
    by_name, by_genus = collections.defaultdict(set), collections.defaultdict(set)
    with open(wals, encoding='utf-8') as f:
        for r in csv.DictReader(f):
            for k in (norm(r['Name']), norm(re.sub(r'\s*\(.*?\)', '', r['Name']))): by_name[k].add(r['Family'])
            by_genus[norm(r['Genus'])].add(r['Family'])
    out = {}
    for d in sorted(os.listdir(langs)):
        if not os.path.isdir(os.path.join(langs, d)): continue
        for table in (by_name, by_genus):
            fams = {f for f in table.get(norm(d), ()) if f and f != 'other'}
            if len(fams) == 1: out[d] = fams.pop(); break
    return out


def table(root):
    return {'Languages': families(root), '@layout': LAYOUT}


if __name__ == '__main__':
    json.dump(table(sys.argv[1] if len(sys.argv) > 1 else os.getcwd()), sys.stdout, indent=0, sort_keys=True)
