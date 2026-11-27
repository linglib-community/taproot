#!/usr/bin/env python3
"""Review priority of every file: how much rests on it times how much its own signals say to look.

Used by `map.py` for the map's "review priority" mode; `landscape.py` takes its weights from here.

Exposure is how far an error in a file travels: for a study, `1 + log2(1 + claims)`, its number of
theorems; for a library file, `1 + log2(1 + studies resting on it) + log2(1 + files above it) / 2`.
The signal score is a weighted mean, by `WEIGHTS`, of signals in [0, 1]:

    decide            uses of `decide` per theorem, at most 1                      every file
    no_claims         the file states no theorem                                   every file
    unused_imports    the share of its imports that none of its declarations use   a measured library file
    stops             the share of its claims whose statement names nothing        a measured study
                      outside the file
    thin              the share of its claims that reach the library through at    a measured study
                      most three of its declarations

Priority is exposure times the signal score. A generated data file has priority 0. The flagged
declarations of `analyze.py` (weight `flagged`) are not computed here, so the mean is over the
signals above; a file with no row in the table has the two text signals only.
"""
import math, os, re

WEIGHTS = {'stops': 1.0, 'thin': 0.5, 'decide': 1.0, 'flagged': 0.8, 'unused_imports': 0.6, 'no_claims': 0.5}
ORDER = ['decide', 'stops', 'thin', 'unused_imports', 'no_claims']        # the page names a signal by its place here
THEOREM = re.compile(r'^\s*(?:@\[[^\]]*\]\s*)*(?:(?:private|protected|public|nonrec)\s+)*theorem\s+([^\s:({\[⦃]+)', re.M)
THIN = 3


def library(m):
    """Core or one of the theory areas: what a claim is meant to rest on."""
    p = m.split('.')
    return p[0] == 'Linglib' and len(p) > 1 and p[1] not in ('Data', 'Languages')


def claim_reach(q, c, m, written):
    """For a theorem `c` of file `m`: whether its statement names anything outside the file, and how
    many written library declarations it reaches (counting stops after `THIN + 1`)."""
    T = q.T
    seen, work, out, lib = {c}, [c], False, set()
    while work:
        for d in q.meaning(work.pop()):
            if d in seen: continue
            seen.add(d); work.append(d)
            md = T['mods'][d]
            if md == m: continue
            out = True
            if library(md) and T['names'][d] in written(md):
                lib.add(d)
                if len(lib) > THIN: return out, len(lib)
    return out, len(lib)


def scores(q, root, mods, G, rest):
    """Per file of `mods`: `(exposure, priority, signals)`, the signals as `[place in ORDER, value]`
    pairs, heaviest first. `G` is the import graph and `rest` what `map.py` measured per file."""
    T = q.T
    ix = {m: i for i, m in enumerate(mods)}
    text = {}
    def src(m):
        if m not in text:
            try: text[m] = open(os.path.join(root, m.replace('.', '/') + '.lean'), encoding='utf-8').read()
            except OSError: text[m] = ''
        return text[m]
    names = {}
    def written(m):
        """Names in the table that the source of `m` declares with a keyword, roughly."""
        if m not in names:
            toks = set(re.findall(r'^\s*(?:@\[[^\]]*\]\s*)*(?:(?:private|protected|noncomputable|public|meta|unsafe|'
                                  r'partial|nonrec|scoped|local)\s+)*(?:theorem|lemma|def|abbrev|structure|inductive|'
                                  r'class|instance|opaque)\s+([^\s:({\[⦃]+)', src(m), re.M))
            names[m] = {T['names'][i] for i in T['by_mod'].get(m, [])
                        if any(T['names'][i] == t or T['names'][i].endswith('.' + t) for t in toks)} if toks else set()
        return names[m]
    above = [0] * len(mods)                               # files that import a file, directly or not
    for m in mods:
        seen, work = set(), list(G[m])
        while work:
            j = work.pop()
            if j in ix and j not in seen: seen.add(j); work.extend(G[j])
        for j in seen: above[ix[j]] += 1
    traffic = [0] * len(mods)                             # studies with a declaration resting on a file
    for k, r in rest.items():
        if mods[k].startswith('Studies.'):
            for x in set(r['n']) | set(r['c']): traffic[x] += 1
    out = []
    for i, m in enumerate(mods):
        s = src(m)
        if m.startswith('Linglib.Data.') and re.search(r'Auto-generated|Do not edit by hand', s[:1500]):
            out.append((0.0, 0.0, [])); continue
        code = re.sub(r'/-.*?-/|--[^\n]*', '', s, flags=re.S)
        thms = THEOREM.findall(code)
        sig = {'decide': min(1.0, len(re.findall(r'\bdecide\b', code)) / len(thms)) if thms else 0.0,
               'no_claims': 0.0 if thms else 1.0}
        if m.startswith('Studies.'):
            cl = []
            if i in rest:
                want = set(thms)
                cl = [c for c in T['by_mod'].get(m, []) if T['kinds'][c] == 'thm' and
                      (T['names'][c] in want or T['names'][c].rsplit('.', 1)[-1] in want or
                       any(T['names'][c].endswith('.' + t) for t in want if '.' in t))]
                if cl:
                    reach = [claim_reach(q, c, m, written) for c in cl]
                    sig['stops'] = sum(1 for o, n in reach if not o) / len(cl)
                    sig['thin'] = sum(1 for o, n in reach if 0 < n <= THIN) / len(cl)
            exposure = 1 + math.log2(1 + (len(cl) or len(thms)))
        else:
            if i in rest and G[m]:
                need = q.need(m)
                sig['unused_imports'] = sum(1 for x in G[m] if x not in need) / len(G[m])
            exposure = 1 + math.log2(1 + traffic[i]) + 0.5 * math.log2(1 + above[i])
        score = sum(WEIGHTS[k] * v for k, v in sig.items()) / sum(WEIGHTS[k] for k in sig)
        top = sorted((k for k in sig if sig[k] > 0), key=lambda k: -WEIGHTS[k] * sig[k])
        out.append((round(exposure, 2), round(exposure * score, 3), [[ORDER.index(k), round(sig[k], 2)] for k in top]))
    return out
