#!/usr/bin/env python3
"""Build the zoomable map: directories, files, declarations.

    map.py [--out FILE] [--base DIR --base-label TEXT] [--groups FILE]

One self-contained page with three levels of the same graph. Directories: what sits at the root of
each, and where another theory area enters. Files: what each names, what is carried to it without
being named, what it imports unused. Declarations: the chain that carries a dependency. Every view
has an address after `#`, so a view can be opened directly: `#d/Syntax.Feature.Person?enter=FILE`
(the directory, tinted downstream of an outside file), `#f/Languages.Basque.Pronouns?why=FILE` (the
file, with the chain that carries FILE to it). Any address also takes `hl=NAME,NAME` (ring those
files or declarations), `note=TEXT` (one line shown beside the path) and `theme=light|dark`. The
directory level needs import lines only; the file level needs the table, and a file without rows in
it is shown by its import lines alone.

With `--base DIR`, a second source tree (say the branch's merge base, from `git archive`), the home
page leads with what changed against it and a directory address takes `vs=1` for before and after.
That comparison reads import lines only, so it needs no table for the base.

With `--groups FILE`, a JSON object `{directory: {child: group}}`, a directory with too many children
to draw as islands (Languages, with its hundred languages) is drawn as one island per group, as
families are. Children the file does not name stay ungrouped; nothing is inferred. Its key `@layout`,
`{directory: {child: [column, row]}}` (`""` for the top level), fixes where islands sit on that
directory's map, for an order the reader already knows; without it the columns follow the imports.

Takes the checkout from `LINGLIB_ROOT` and the table from `TAPROOT_TABLE`, as `query.py` does.
"""
import argparse, importlib.util, json, os, re, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))

COMMENT = re.compile(r'/-.*?-/|--[^\n]*|"(?:[^"\\\n]|\\.)*"', re.S)       # comments and string literals

def source_counts(root, mods):
    """Per file, outside comments and strings: occurrences of `decide +kernel`, and how many
    mathlib files it imports directly."""
    kd, ml = [], []
    for m in mods:
        try: raw = open(os.path.join(root, m.replace('.', '/') + '.lean'), encoding='utf-8').read()
        except OSError: raw = ''
        text = COMMENT.sub('', raw)
        ml.append(len(re.findall(r'^\s*(?:public\s+)?(?:meta\s+)?import\s+Mathlib\.', raw, re.M)))
        kd.append(len(re.findall(r'\bdecide\s*\+kernel\b', text)))
    return dict(kd=kd, ml=ml)

def titles(root, mods):
    """Per file, the title of its module docstring: the first `# ` line inside the first `/-! -/`."""
    out = []
    for m in mods:
        t = ''
        try:
            head = open(os.path.join(root, m.replace('.', '/') + '.lean'), encoding='utf-8').read(6000)
            doc = re.search(r'/-!(.*?)(?:-/|\Z)', head, re.S)
            line = re.search(r'^#\s+(.+)$', doc.group(1), re.M) if doc else None
            if line: t = line.group(1).strip()
        except OSError: pass
        out.append(t)
    return out

def build(out, base=None, base_label='', groups=None, label=''):
    spec = importlib.util.spec_from_file_location('query', os.path.join(HERE, 'query.py'))
    q = importlib.util.module_from_spec(spec); spec.loader.exec_module(q)
    T, G, short = q.T, q.imports(), q.short
    mods = sorted(G); ix = {m: i for i, m in enumerate(mods)}
    imp = [[ix[i] for i in G[m] if i in ix] for m in mods]
    rest = {}
    for k, m in enumerate(mods):
        if m not in T['by_mod']: continue
        named, proof, carried = q.rests(m)
        rest[k] = dict(
            n={ix[x]: len(v) for x, v in named.items() if x in ix},
            c={ix[x]: [[T['names'][i], ix.get(T['mods'][i], -1)] for i in ch] for x, ch in carried.items() if x in ix},
            p=sorted(ix[x] for x in proof if x in ix and x not in named and x not in carried))
    rank, seen = [], set()
    for ru, us, d, r, t in q.roots(G):
        if (d, t) in seen: continue
        seen.add((d, t)); rank.append([ru, us, short(d), ix[r], ix[t]])
    try: commit = subprocess.run(['git', '-C', q.ROOT, 'log', '-1', '--format=%h %cd', '--date=short'],
                                 capture_output=True, text=True).stdout.strip()
    except Exception: commit = ''
    meta = dict(commit=label or commit, files=len(mods), measured=len(rest))
    old = None
    if base:
        head_root, q.ROOT = q.ROOT, os.path.abspath(base)
        G0 = q.imports(); q.ROOT = head_root
        mods0 = sorted(G0); ix0 = {m: i for i, m in enumerate(mods0)}
        rank0, seen0 = [], set()
        for ru, us, d, r, t in q.roots(G0):
            if (d, t) in seen0: continue
            seen0.add((d, t)); rank0.append([ru, us, short(d), short(r), short(t)])
        old = dict(files=[short(m) for m in mods0], imp=[[ix0[i] for i in G0[m] if i in ix0] for m in mods0],
                   rank=rank0[:400], label=base_label or os.path.basename(os.path.abspath(base)))
    page = open(os.path.join(HERE, 'map.html'), encoding='utf-8').read()
    for key, val in (('__FILES__', [short(m) for m in mods]), ('__IMP__', imp), ('__REST__', rest),
                     ('__RANK__', rank[:400]), ('__META__', meta), ('__BASE__', old),
                     ('__SRC__', source_counts(q.ROOT, mods)), ('__TITLES__', titles(q.ROOT, mods)),
                     ('__GROUPS__', json.load(open(groups, encoding='utf-8')) if groups else {})):
        page = page.replace(key, json.dumps(val, separators=(',', ':')))
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    open(out, 'w', encoding='utf-8').write(page)
    print(f'{out}: {len(mods)} files, {len(rest)} measured, {len(rank)} root crossings')

if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--out', default=os.path.join(os.environ.get('LINGLIB_ROOT', os.getcwd()), '.lake/build/taproot/map.html'))
    ap.add_argument('--base', help='a second source tree to compare against, by import lines')
    ap.add_argument('--base-label', default='', help='how to name the base on the page, e.g. its commit')
    ap.add_argument('--groups', help='JSON {directory: {child: group}} for directories drawn by group')
    ap.add_argument('--label', default='', help='what to call this build on the page, when the tree is not a git checkout')
    a = ap.parse_args()
    build(a.out, a.base, a.base_label, a.groups, a.label)
