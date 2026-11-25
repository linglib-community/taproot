#!/usr/bin/env python3
"""Place every hand-written file on a plane, near the files its declarations use.

    python3 tendrils/landscape.py GRAPH_JSON OUT_DIR [--source DIR] [--weights FILE]

Reads the `graph.json` of `analyze.py` and writes `landscape.json` to `OUT_DIR`: one row per file, in
the order of the files in `graph.json`, holding x, y, the file's exposure, its suspicion and its uses
of `decide` per theorem, or `null` for a generated data file, which is left off the map. The page
draws the map from it and hides the map where the file is absent.

Two files are close when their declarations use the same files or are used by the same files. Each
file is a vector over the others (1 for a file it uses, 0.3 for one it only imports, 0.6 for a file
that uses it), weighted so that a file everything uses counts for little; the vectors are reduced
by a truncated SVD and laid out by t-SNE. Each coordinate is then mixed with its rank and any two
points closer than a fixed gap are pushed apart, so that every file can be picked out. Distances
between neighbourhoods and the axes carry no meaning.

Exposure is how much rests on a file: for a study its number of theorems, for a library file the
studies whose claims rest on it and the files above it. Suspicion is a weighted mean of signals in
[0, 1]: for every file, uses of `decide` per theorem, whether it has a flagged declaration, and
whether it states no theorem; for a study, the shares of its claims that stop in the file and that
reach the library thinly; for a library file, the share of its imports that go unused. `--weights`
names a JSON object of weights by signal that replaces `WEIGHTS`. `--source` (default `LINGLIB_ROOT`
or the current directory) is where the files' text is read; pass the tree `graph.json` was measured
on.

Needs numpy, scipy and scikit-learn. `gen_tendrils.py` skips this step where they are missing.
"""
import argparse, json, math, os, re

import numpy as np
from scipy import sparse
from scipy.spatial import cKDTree
from sklearn.decomposition import TruncatedSVD
from sklearn.manifold import TSNE

ROOT = os.path.abspath(os.environ.get('LINGLIB_ROOT', os.getcwd()))
WEIGHTS = {'stops': 1.0, 'thin': 0.5, 'decide': 1.0, 'flagged': 0.8, 'unused_imports': 0.6, 'no_claims': 0.5}
GAP = 0.0075          # least distance between two points, the map being the unit square


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('graph'); ap.add_argument('out')
    ap.add_argument('--source', default=ROOT); ap.add_argument('--weights')
    args = ap.parse_args()
    graph, out, src = args.graph, args.out, args.source
    W = {**WEIGHTS, **(json.load(open(args.weights)) if args.weights else {})}
    rows = json.load(open(graph, encoding='utf-8'))
    mods = [r for r in rows if r[0] == 'M']   # name 1, layer 2, imports 6, used 7, traffic 10, imports 14, uses 15, flags 17
    claims = {r[1]: r[2] for r in rows if r[0] == 'C'}
    n = len(mods)
    above = [0] * n                                   # files that import a file, directly or not
    for m in mods:
        seen, work = set(), list(m[14])
        while work:
            j = work.pop()
            if j not in seen: seen.add(j); work.extend(mods[j][14])
        for j in seen: above[j] += 1
    exposure, decide, generated, susp = [], [], [], []
    for i, m in enumerate(mods):
        try: text = open(os.path.join(src, m[1].replace('.', '/') + '.lean'), encoding='utf-8').read()
        except OSError: text = ''
        thm = len(re.findall(r'^(?:@\[[^\]]*\]\s*)?theorem ', text, re.M))
        decide.append(min(1.0, len(re.findall(r'\bdecide\b', text)) / thm) if thm else None)
        generated.append(m[1].startswith('Linglib.Data.') and
                         bool(re.search(r'Auto-generated|Do not edit by hand', text[:1500])))
        sig = {'decide': decide[-1] or 0.0, 'flagged': 1.0 if m[17] else 0.0, 'no_claims': 0.0 if thm else 1.0}
        if m[2] == 'study':
            cl = claims.get(i, [])          # a claim: declaration, class, headline, shared declarations
            lvl = [(1 if c[3] <= 3 else 0) if c[1] == 0 else (2 if c[1] <= 2 else c[1]) for c in cl]
            sig['stops'] = sum(1 for x in lvl if x >= 3) / len(cl) if cl else 0.0
            sig['thin'] = sum(1 for x in lvl if x == 1) / len(cl) if cl else 0.0
            exposure.append(1 + math.log2(1 + len(cl)))
        else:
            sig['unused_imports'] = 1 - m[7] / m[6] if m[6] else 0.0
            exposure.append(1 + math.log2(1 + m[10]) + 0.5 * math.log2(1 + above[i]))
        susp.append(sum(W[k] * v for k, v in sig.items()) / sum(W[k] for k in sig))
    r_, c_, v_ = [], [], []
    for i, m in enumerate(mods):
        use = set(m[15])
        for j in use: r_.append(i); c_.append(j); v_.append(1.0)
        for j in set(m[14]) - use: r_.append(i); c_.append(j); v_.append(0.3)
    X = sparse.csr_matrix((v_, (r_, c_)), shape=(n, n))
    keep = np.array([i for i in range(n) if not generated[i]])
    A = (X + 0.6 * X.T).tocsr()[keep][:, keep]
    k = len(keep)
    idf = np.log(k / (1.0 + np.asarray((A > 0).sum(axis=0)).ravel())) + 0.2
    A = A @ sparse.diags(idf)
    norm = np.sqrt(np.asarray(A.multiply(A).sum(axis=1)).ravel()); norm[norm == 0] = 1
    Z = TruncatedSVD(n_components=48, random_state=0).fit_transform(sparse.diags(1 / norm) @ A)
    T = TSNE(n_components=2, perplexity=40, metric='cosine', init='random', random_state=0,
             learning_rate='auto', max_iter=1500).fit_transform(Z)
    unit = lambda M: (M - M.min(0)) / (M.max(0) - M.min(0))
    T = unit(T)
    near = cKDTree(T).query(T, k=11)[1][:, 1:]
    T = 0.5 * T + 0.5 * np.argsort(np.argsort(T, axis=0), axis=0) / (k - 1)
    T = T + np.random.default_rng(0).normal(0, 1e-4, T.shape)
    for _ in range(120):
        pairs = cKDTree(T).query_pairs(GAP, output_type='ndarray')
        if not len(pairs): break
        d = T[pairs[:, 0]] - T[pairs[:, 1]]; dist = np.linalg.norm(d, axis=1) + 1e-9
        push = d / dist[:, None] * ((GAP - dist) / 2)[:, None] * 0.6
        np.add.at(T, pairs[:, 0], push); np.add.at(T, pairs[:, 1], -push)
    T = unit(T)
    kept = np.mean([len(set(a) & set(b)) / 10 for a, b in zip(near, cKDTree(T).query(T, k=11)[1][:, 1:])])
    xy = {int(i): T[p] for p, i in enumerate(keep)}
    r3 = lambda v: None if v is None else round(float(v), 3)
    with open(os.path.join(out, 'landscape.json'), 'w', encoding='utf-8') as fh:
        fh.write('[\n' + ',\n'.join(
            json.dumps(None if generated[i] else
                       [round(float(xy[i][0]), 4), round(float(xy[i][1]), 4), r3(exposure[i]), r3(susp[i]),
                        r3(decide[i])])
            for i in range(n)) + '\n]\n')
    print(f'{k} files placed, {n - k} generated files left off; '
          f'{kept:.0%} of each file\'s ten nearest neighbours survive the spacing')


if __name__ == '__main__':
    main()
