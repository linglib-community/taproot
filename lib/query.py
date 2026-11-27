#!/usr/bin/env python3
"""Ask the declaration table questions.

    query.py users DECL...            files whose declarations mention DECL (or anything under it)
    query.py thin [FILE|DIR]          a file's declarations by how many other files name each, rest on each, and
                                      rest on the file through that one alone; with no file, files ranked by
                                      how many import them without using them
    query.py own [FILE|DIR]           who owns the substrate: each declaration is shared (two consumer files reach
                                      it by separate routes), behind one shared declaration, reached from one
                                      consumer file, or reached from none; for a file, per declaration
    query.py rot [FILE|DIR]           the unreached substrate by kind: unused theorems about live objects, against
                                      concepts nothing exercises (dead definitions and what rests on them),
                                      with the root definitions ranked by what was built on them
    query.py needs MODULE             what a file imports against what its declarations use
    query.py cone MODULE              each imported file: named by this file, or carried by what?
    query.py why MODULE TARGET        the chains of declarations by which MODULE rests on TARGET
    query.py roots                    directories whose root files import another theory area
    query.py up MODULE                what rests on a file: who names it, who has it carried, through what
    query.py hot [DIR]                directories by the share of their users that inherit another theory area
    query.py changed OLD_TABLE [MODULE...]   against an older table: what each file newly carries or no longer does
    query.py slow [N]                 the N files that took longest to build, and how many files wait on each
    query.py cut MODULE IMPORT        remove one import line: who loses something they use
    query.py move NEWMODULE DECL...   move declarations to a new file importing their old one

The table lists the named declarations of the compiled library, so a use inside an `example` (or any
command that adds no constant) is not seen: 'no user' and 'unreached' are leads to check with a build.

The table is parsed once and cached beside it. Files with no row in the table are unmeasured: the
answers say how many of those sit above a cut, since only a build can check them.
"""
import collections, functools, os, pickle, re, sys

ROOT = os.path.abspath(os.environ.get('LINGLIB_ROOT', os.getcwd()))    # the linglib checkout
TABLE = os.environ.get('TAPROOT_TABLE', os.path.join(ROOT, '.lake/build/declaration-dependencies/table.tsv'))
IMPORT = re.compile(r'^(?:public )?(?:meta )?import (?:all )?((?:Linglib|Studies)\.\S+)')
sys.setrecursionlimit(30000)
short = lambda m: m.replace('Linglib.', '')

def load(table=None):
    table = table or TABLE
    cache = table + '.idx4'
    if os.path.exists(cache) and os.path.getmtime(cache) > os.path.getmtime(table):
        return pickle.load(open(cache, 'rb'))
    names, mods, deps, kinds, tdeps, vdeps, flags, lines = [], [], [], [], [], [], [], []
    for line in open(table, encoding='utf-8'):
        f = line.rstrip('\n').split('\t')
        names.append(f[0]); mods.append(f[1]); kinds.append(f[2]); flags.append(f[3])
        lines.append((int(f[11]), int(f[12])) if len(f) > 12 else (0, 0))   # first and last source line, 0 if unknown
        tdeps.append(tuple({int(x) for x in f[4].split(',') if x}))
        vdeps.append(tuple({int(x) for x in f[5].split(',') if x}))
        deps.append(tuple(set(tdeps[-1]) | set(vdeps[-1])))
    rdeps = collections.defaultdict(list)
    for i, ds in enumerate(deps):
        for d in ds: rdeps[d].append(i)
    by_name = collections.defaultdict(list)
    for i, n in enumerate(names): by_name[n].append(i)
    by_mod = collections.defaultdict(list)
    for i, m in enumerate(mods): by_mod[m].append(i)
    idx = dict(names=names, mods=mods, deps=deps, rdeps=dict(rdeps), by_name=dict(by_name), by_mod=dict(by_mod),
               kinds=kinds, tdeps=tdeps, vdeps=vdeps, flags=flags, lines=lines)
    pickle.dump(idx, open(cache, 'wb'))
    return idx

def imports():
    G = {}
    for top in ('Linglib', 'Studies'):
        for dp, _, fs in os.walk(os.path.join(ROOT, top)):
            for f in fs:
                if f.endswith('.lean'):
                    p = os.path.join(dp, f)
                    m = os.path.relpath(p, ROOT)[:-5].replace('/', '.')
                    with open(p, encoding='utf-8') as fh:
                        G[m] = [x.group(1) for x in map(IMPORT.match, fh) if x]
    return G

def closure(G):
    @functools.lru_cache(None)
    def c(m):
        s = set()
        for i in G.get(m, []): s.add(i); s |= c(i)
        return frozenset(s)
    return c

T = load()

def ids_of(decl):
    """A declaration with everything generated under its name."""
    return [i for n, ids in T['by_name'].items() if n == decl or n.startswith(decl + '.') for i in ids]

@functools.lru_cache(None)
def need(m):
    """The files the declarations of `m` use, proofs included."""
    seen, work = set(), list(T['by_mod'].get(m, []))
    seen.update(work)
    while work:
        for d in T['deps'][work.pop()]:
            if d not in seen: seen.add(d); work.append(d)
    return frozenset(T['mods'][i] for i in seen) - {m}

def users(decls):
    out = collections.Counter()
    for d in decls:
        own = set(ids_of(d))
        if not own: print('not in the table:', d); continue
        home = T['mods'][next(iter(own))]
        for i in own:
            for u in T['rdeps'].get(i, []):
                if u not in own and T['mods'][u] != home: out[T['mods'][u]] += 1
    return out

def meaning(c, tab=None):
    """What a declaration's meaning rests on: a theorem's statement, a definition's type and body."""
    tab = tab or T
    return tab['tdeps'][c] if tab['kinds'][c] == 'thm' else tab['deps'][c]

def rests(m, tab=None):
    """How the file `m` comes to rest on each other file. Returns, per file, `named` (declarations of
    `m` whose statement or definition names something there), `proof` (those that use it only in a
    proof) and `carried` (a chain `[own, carrier, ..., target]` when nothing in `m` names it)."""
    tab = tab or T
    own = tab['by_mod'].get(m, [])
    named, proof = collections.defaultdict(set), collections.defaultdict(set)
    par, depth, work = {}, {}, collections.deque()
    for i in own:
        seeds = set(meaning(i, tab))
        for d in seeds:
            if tab['mods'][d] != m: named[tab['mods'][d]].add(i)
            if d not in depth: depth[d] = 1; par[d] = i; work.append(d)
        if tab['kinds'][i] == 'thm':
            for d in set(tab['vdeps'][i]) - seeds:
                if tab['mods'][d] != m: proof[tab['mods'][d]].add(i)
    carried = {}
    while work:
        c = work.popleft()
        mc = tab['mods'][c]
        if mc != m and mc not in named and mc not in carried:
            chain = [c]
            while chain[-1] in par and chain[-1] not in own: chain.append(par[chain[-1]])
            carried[mc] = chain[::-1]
        for d in meaning(c, tab):
            if d not in depth: depth[d] = depth[c] + 1; par[d] = c; work.append(d)
    return named, proof, carried

THEORY = {'Semantics', 'Syntax', 'Pragmatics', 'Morphology', 'Phonology', 'Processing', 'Discourse', 'Logic'}

def area(m):
    p = m.split('.')
    return p[1] if p[0] == 'Linglib' and len(p) > 1 else p[0]

def roots(G, min_files=4, min_users=25):
    """Directories of the theory layer whose root files (those importing nothing else in the directory)
    import another theory area: rows `(users reaching the root file, all users, directory, root file,
    imported file)`, most inherited first. Import paths only, so these are candidates, not verdicts."""
    c = closure(G)
    dirs = collections.defaultdict(list)
    for m in G:
        p = m.split('.')
        if p[0] == 'Linglib' and len(p) > 2 and p[1] in THEORY:
            for k in range(3, len(p)): dirs['.'.join(p[:k])].append(m)
    rows = []
    for d, fs in dirs.items():
        if len(fs) < min_files: continue
        S = set(fs)
        users = [u for u in G if u not in S and c(u) & S]
        if len(users) < min_users: continue
        for r in fs:
            if any(i in S for i in G[r]): continue
            ru = sum(1 for u in users if r in c(u))
            for t in G[r]:
                if t not in S and area(t) in THEORY and area(t) != area(d):
                    rows.append((ru, len(users), d, r, t))
    return sorted(rows, reverse=True)

def show_name(i): return f"{T['names'][i]} [{short(T['mods'][i])}]"

def simulate(G2, G, label):
    c0, c1 = closure(G), closure(G2)
    lost, unmeasured = {}, []
    for m in G:
        gone = c0(m) - c1(m)
        if not gone: continue
        if m not in T['by_mod']: unmeasured.append(m); continue
        miss = need(m) & gone
        if miss: lost[m] = miss
    a, b = sum(len(c0(m)) for m in G), sum(len(c1(m)) for m in G)
    print(f'{label}: summed import closure {a} -> {b}')
    print(f'{len(lost)} measured files lose a file they use:')
    for m in sorted(lost):
        tops = [x for x in lost[m] if not any(x in c0(y) for y in lost[m] if y != x)]
        print('   ', short(m), '+ import', ', '.join(short(x) for x in sorted(tops)))
    print(f'{len(unmeasured)} unmeasured files sit above the cut; a build has to check them')
    return lost, unmeasured

def written(m):
    """The declarations of `m` that someone wrote, each with everything generated under its name
    (matchers, proofs, constructors, recursors): `{declaration: [ids]}`."""
    ids = T['by_mod'].get(m, [])
    auto = ('casesOn', 'recOn', 'rec', 'noConfusion', 'noConfusionType', 'below', 'brecOn', 'ctorIdx', 'toCtorIdx',
            'ofNat', 'sizeOf_spec', 'injEq', 'inj', 'ext', 'ext_iff', 'mk', 'ctorElim', 'ctorElimType', 'elim')
    own = {T['names'][i]: i for i in ids if 'i' not in T['flags'][i] and T['kinds'][i] not in ('ctor', 'rec')
           and T['names'][i].rsplit('.', 1)[-1] not in auto}
    out = {own[n]: [own[n]] for n in own}
    for i in ids:
        n = T['names'][i]
        if n in own: continue
        while '.' in n and n not in own: n = n.rsplit('.', 1)[0]
        if n in own: out[own[n]].append(i)
    return out

def fan_in(m):
    """Per written declaration of `m`: the other files that mention it, and how many declarations of
    `m` itself do."""
    rows = []
    for d, ids in written(m).items():
        own, outside, inside = set(ids), set(), set()
        for i in ids:
            for u in T['rdeps'].get(i, []):
                if u in own: continue
                (inside if T['mods'][u] == m else outside).add(T['mods'][u] if T['mods'][u] != m else u)
        rows.append((len(outside), T['names'][d], sorted(outside), len(inside)))
    return sorted(rows)

def used_by():
    """Per file, the files with a declaration that rests on one of its declarations, proofs included."""
    bit = {m: 1 << k for k, m in enumerate(T['by_mod'])}
    reach = [0] * len(T['names']); state = bytearray(len(T['names']))
    for root in range(len(T['names'])):
        if state[root]: continue
        stack = [root]; state[root] = 1
        while stack:
            i = stack[-1]
            todo = [d for d in T['deps'][i] if not state[d]]
            if todo:
                for d in todo: state[d] = 1
                stack.extend(todo); continue
            stack.pop(); r = bit[T['mods'][i]]
            for d in T['deps'][i]: r |= reach[d]
            reach[i] = r
    users = collections.Counter()
    for m, ids in T['by_mod'].items():
        r = 0
        for i in ids: r |= reach[i]
        r &= ~bit[m]
        for f, b in bit.items():
            if r & b: users[f] += 1
    return users

CONSUMER = lambda m: m.startswith('Studies.') or m.startswith('Linglib.Languages.')

def owners():
    """The dominator tree of the declaration graph under a root above the consumer files (studies and
    language files), one node per consumer file between the root and that file's declarations. Returns
    `status` and `entry` per written declaration that is not a consumer's: `status` is 'surface' (the
    root is its dominator: two consumer files reach it by separate routes), 'behind' (every route
    passes through the surface declaration `entry`), 'one file' (every route starts in the consumer
    file `entry`) or 'unreached'."""
    N = len(T['names']); own = list(range(N))
    for m in T['by_mod']:
        for d, ids in written(m).items():
            for i in ids: own[i] = d
    wr = {i for i in range(N) if own[i] == i and 'i' not in T['flags'][i]}
    succ = collections.defaultdict(set)
    for i in range(N):
        a = own[i]
        if a in wr:
            for d in T['deps'][i]:
                if own[d] in wr and own[d] != a: succ[a].add(own[d])
    ROOT, fnode = -1, {}
    for v in wr:
        if CONSUMER(T['mods'][v]): succ[fnode.setdefault(T['mods'][v], -2 - len(fnode))].add(v)
    succ[ROOT] = set(fnode.values()); fname = {f: m for m, f in fnode.items()}
    order, seen, stack = [], {ROOT}, [(ROOT, iter(succ[ROOT]))]
    while stack:
        v, it = stack[-1]
        for w in it:
            if w not in seen: seen.add(w); stack.append((w, iter(succ.get(w, ())))); break
        else: stack.pop(); order.append(v)
    order.reverse(); rpo = {v: k for k, v in enumerate(order)}
    pred = collections.defaultdict(list)
    for a in order:
        for b in succ.get(a, ()): pred[b].append(a)
    idom, changed = {ROOT: ROOT}, True
    def meet(a, b):
        while a != b:
            while rpo[a] > rpo[b]: a = idom[a]
            while rpo[b] > rpo[a]: b = idom[b]
        return a
    while changed:
        changed = False
        for v in order[1:]:
            new = None
            for p in pred[v]:
                if p in idom: new = p if new is None else meet(p, new)
            if idom.get(v) != new: idom[v] = new; changed = True
    top = {}
    for v in order[1:]: top[v] = v if idom[v] == ROOT else top[idom[v]]
    status, entry = {}, {}
    for v in wr:
        m = T['mods'][v]
        if CONSUMER(m) or m.startswith('Linglib.Data.'): continue
        if v not in rpo: status[v] = 'unreached'; continue
        e = top[v]
        status[v] = 'one file' if e < 0 else 'surface' if e == v else 'behind'
        if e != v: entry[v] = fname[e] if e < 0 else e
    return status, entry

def rot():
    """Sorts the unreached declarations of `owners()`. Returns `kind` per unreached declaration
    ('unused theorem': it rests on no dead definition; 'dead definition'; 'on a dead definition') and
    `tower` per root, a dead definition resting on no other: every dead declaration above it."""
    status, _ = owners()
    N = len(T['names']); own = list(range(N))
    for m in T['by_mod']:
        for d, ids in written(m).items():
            for i in ids: own[i] = d
    rd = collections.defaultdict(set)
    for i in range(N):
        a = own[i]
        if a in status:
            for d in T['deps'][i]:
                if own[d] in status and own[d] != a: rd[own[d]].add(a)
    dead = {v for v, k in status.items() if k == 'unreached'}
    isdef = lambda v: T['kinds'][v] in ('def', 'ind', 'opaque')
    def above(starts):
        seen, st = set(), list(starts)
        while st:
            for u in rd[st.pop()]:
                if u in dead and u not in seen: seen.add(u); st.append(u)
        return seen
    tainted = above(v for v in dead if isdef(v))
    kind = {v: 'dead definition' if isdef(v) else 'on a dead definition' if v in tainted else 'unused theorem' for v in dead}
    tower = {v: above([v]) | {v} for v in dead if isdef(v) and v not in tainted}
    return status, kind, tower

def main(argv):
    cmd, args = argv[0], argv[1:]
    if cmd == 'users':
        u = users(args)
        for m, n in sorted(u.items()): print(f'{n:4d}  {short(m)}')
        print(len(u), 'files')
    elif cmd == 'thin':
        G = imports(); rev = collections.defaultdict(list)
        for x, ims in G.items():
            for i in ims: rev[i].append(x)
        def above(m):
            up, st = set(), [m]
            while st:
                for y in rev[st.pop()]:
                    if y not in up: up.add(y); st.append(y)
            return len(up)
        a = args[0] if args else ''
        m = a if a.startswith(('Linglib.', 'Studies.')) else 'Linglib.' + a
        if a and m in T['by_mod']:
            rows = fan_in(m); through = {}
            for d, ids in written(m).items():      # the files that rest on each declaration, at any distance
                seen, work = set(ids), list(ids)
                while work:
                    for u in T['rdeps'].get(work.pop(), []):
                        if u not in seen: seen.add(u); work.append(u)
                through[T['names'][d]] = {T['mods'][i] for i in seen} - {m}
            routes = collections.Counter(f for fs in through.values() for f in fs)
            use = len(routes)
            n = collections.Counter(min(r[0], 2) for r in rows)
            print(f'{short(m)}: {above(m)} files import it, {use} use a declaration of it')
            print(f'{len(rows)} declarations: {n[0]} used by no other file, {n[1]} by one, {n[2]} by more')
            print('  named by  rest on it  only route   declaration')
            for k, name, outside, inside in rows:
                fs = through[name]; sole = sum(1 for f in fs if routes[f] == 1)
                where = ', '.join(short(x) for x in outside[:2]) + (f' (+{k - 2})' if k > 2 else '')
                print(f'   {k:7d}  {len(fs):10d}  {sole:10d}   {name:40} {where}' +
                      (f'only inside the file, by {inside}' if not k and inside else ''))
        else:
            pre = m + '.' if a else 'Linglib.'
            use = used_by(); rows = []
            for f in T['by_mod']:
                if not f.startswith(pre) or f.split('.')[1] in ('Languages', 'Data'): continue
                fi = fan_in(f)
                if not fi: continue
                n = collections.Counter(min(r[0], 2) for r in fi); imp = above(f)
                rows.append((imp - use[f], imp, use[f], len(fi), n[0], n[1], f))
            print('import it  use it  declarations  used by no file  by one   file')
            for _, imp, u, k, n0, n1, f in sorted(rows, reverse=True)[:int(os.environ.get('TAPROOT_TOP', 25))]:
                print(f'{imp:9d}  {u:6d}  {k:12d}  {n0:15d}  {n1:6d}   {short(f)}')
    elif cmd == 'own':
        status, entry = owners(); a = args[0] if args else ''
        m = a if a.startswith(('Linglib.', 'Studies.')) else 'Linglib.' + a
        KS = ('surface', 'behind', 'one file', 'unreached')
        say = lambda e: short(e) if isinstance(e, str) else T['names'][e]
        if a and m in T['by_mod']:
            vs = [v for v in status if T['mods'][v] == m]; c = collections.Counter(status[v] for v in vs)
            print(f'{short(m)}: ' + ', '.join(f'{c[k]} {k}' for k in KS if c[k]))
            for v in sorted(vs, key=lambda v: (KS.index(status[v]), T['names'][v])):
                print(f'   {status[v]:10} {T["names"][v]:44}' + (f' <- {say(entry[v])}' if v in entry else ''))
        else:
            pre = (m + '.') if a else 'Linglib.'
            vs = [v for v in status if T['mods'][v].startswith(pre)]; c = collections.Counter(status[v] for v in vs)
            print(f'{len(vs)} written declarations' + (f' under {short(m)}' if a else ' in the theory layer and Core'))
            for k in KS: print(f'   {c[k]:6d}  {100 * c[k] / max(len(vs), 1):4.1f}%  {k}')
            per, cons = collections.defaultdict(collections.Counter), collections.defaultdict(collections.Counter)
            for v in vs:
                per[T['mods'][v]][status[v]] += 1
                if status[v] == 'one file': cons[T['mods'][v]][entry[v]] += 1
            top = int(os.environ.get('TAPROOT_TOP', 15))
            rows = [(k['one file'], sum(k.values()), f, cons[f].most_common(1)[0][0]) for f, k in per.items()
                    if k['one file'] >= 8 and not k['surface'] and not k['behind'] and len(cons[f]) == 1]
            print(f'{len(rows)} files serve one consumer file and nothing else:')
            for n, t, f, e in sorted(rows, reverse=True)[:top]: print(f'   {n:4d} of {t:4d}  {short(f):58} -> {short(e)}')
            dead = [(sum(k.values()), f) for f, k in per.items() if k['unreached'] == sum(k.values())]
            print(f'{len(dead)} files are reached by no consumer file:')
            for n, f in sorted(dead, reverse=True)[:top]: print(f'   {n:4d}  {short(f)}')
            gate = collections.Counter(entry[v] for v in vs if status[v] == 'behind')
            print('surface declarations with the most substrate reachable only through them:')
            for e, n in gate.most_common(top): print(f'   {n:4d}  {T["names"][e]}  [{short(T["mods"][e])}]')
    elif cmd == 'rot':
        status, kind, tower = rot(); a = args[0] if args else ''
        m = a if a.startswith(('Linglib.', 'Studies.')) else 'Linglib.' + a
        if a and m in T['by_mod']:
            root = {}
            for r, vs in sorted(tower.items(), key=lambda kv: len(kv[1])):
                for v in vs: root[v] = r
            vs = [v for v in status if T['mods'][v] == m]; c = collections.Counter(kind.get(v, 'live') for v in vs)
            print(f'{short(m)}: ' + ', '.join(f'{n} {k}' for k, n in c.most_common()))
            for v in sorted(vs, key=lambda v: (kind.get(v, 'live'), T['names'][v])):
                if v in kind:
                    r = root.get(v)
                    print(f'   {kind[v]:20} {T["names"][v]:44}' + (f' <- {T["names"][r]}' if r is not None and r != v else ''))
        else:
            pre = (m + '.') if a else 'Linglib.'
            inp = lambda v: T['mods'][v].startswith(pre)
            vs = [v for v in status if inp(v)]; c = collections.Counter(kind.get(v, 'live') for v in vs)
            print(f'{len(vs)} written declarations' + (f' under {short(m)}' if a else ' in the theory layer and Core'))
            for k in ('live', 'unused theorem', 'dead definition', 'on a dead definition'):
                print(f'   {c[k]:6d}  {100 * c[k] / max(len(vs), 1):4.1f}%  {k}')
            roots = sorted((r for r in tower if inp(r)), key=lambda r: -len(tower[r]))
            print(f'{len(roots)} root concepts: dead definitions that rest only on live substrate. By what was built on them:')
            for r in roots[:int(os.environ.get('TAPROOT_TOP', 20))]:
                fs = {T['mods'][u] for u in tower[r]}
                print(f'   {len(tower[r]) - 1:4d} declarations in {len(fs):2d} files   {T["names"][r]}  [{short(T["mods"][r])}]')
    elif cmd == 'needs':
        m = args[0] if args[0].startswith(('Linglib.', 'Studies.')) else 'Linglib.' + args[0]
        G = imports(); c = closure(G); nd = need(m)
        print(f'{short(m)}: imports {len(c(m))} files, uses {len(nd & c(m))}')
        for i in G[m]:
            got = ({i} | c(i)) & nd
            print(f'   {short(i):58} uses {len(got):3d} of {len(c(i)) + 1}')
    elif cmd == 'cone':
        m = args[0] if args[0].startswith(('Linglib.', 'Studies.')) else 'Linglib.' + args[0]
        G = imports(); c = closure(G)(m)
        named, proof, carried = rests(m)
        lib = lambda x: x.startswith(('Linglib.', 'Studies.'))
        nm = sorted(x for x in named if lib(x)); ca = sorted(x for x in carried if lib(x))
        pf = sorted(x for x in proof if lib(x) and x not in named and x not in carried)
        un = sorted(x for x in c if x not in named and x not in carried and x not in proof)
        print(f'{short(m)}: imports {len(c)} files')
        print(f'named by this file ({len(nm)}):')
        for x in nm: print(f'   {short(x):50} by {len(named[x])} of its declarations')
        print(f'carried, never named here ({len(ca)}):')
        by = collections.defaultdict(list)
        for x in ca: by[carried[x][1] if len(carried[x]) > 1 else carried[x][0]].append(x)
        for car, xs in sorted(by.items(), key=lambda kv: -len(kv[1])):
            print(f'   through {show_name(car)}:')
            for x in xs: print(f'      {short(x)}')
        print(f'used in proofs only ({len(pf)}): ' + ', '.join(short(x) for x in pf))
        print(f'imported and unused ({len(un)}): ' + ', '.join(short(x) for x in un))
    elif cmd == 'why':
        m, t = (a if a.startswith(('Linglib.', 'Studies.')) else 'Linglib.' + a for a in args[:2])
        named, proof, carried = rests(m)
        if t in named:
            print(f'{short(m)} names {short(t)} itself, in {len(named[t])} declarations:')
            for i in sorted(named[t], key=lambda i: T['names'][i])[:12]:
                hits = sorted({T['names'][d] for d in meaning(i) if T['mods'][d] == t})[:4]
                print(f"   {T['names'][i]}  ->  {', '.join(hits)}")
        elif t in carried:
            print(f'{short(m)} never names {short(t)}; it is carried:')
            print('   ' + '\n   -> '.join(show_name(i) for i in carried[t]))
        elif t in proof:
            print(f'{short(m)} uses {short(t)} only inside proofs ({len(proof[t])} declarations)')
        else:
            print(f'no declaration of {short(m)} rests on {short(t)}')
    elif cmd == 'roots':
        seen = set()
        for ru, us, d, r, t in roots(imports()):
            if (d, t) in seen: continue
            seen.add((d, t))
            print(f'{ru:4d} of {us:4d}  {short(d):36} {short(r)[len(short(d)) + 1:]:24} imports {short(t)}')
            if len(seen) >= int(args[0]) if args else len(seen) >= 30: break
    elif cmd == 'up':
        m = args[0] if args[0].startswith(('Linglib.', 'Studies.')) else 'Linglib.' + args[0]
        G = imports(); rev = collections.defaultdict(list)
        for x, ims in G.items():
            for i in ims: rev[i].append(x)
        up, st = set(), [m]
        while st:
            for y in rev[st.pop()]:
                if y not in up: up.add(y); st.append(y)
        kind, via = collections.Counter(), collections.Counter()
        layer = lambda y: y.split('.')[1] if y.startswith('Linglib.') and y.split('.')[1] in ('Languages', 'Data') else \
            'Studies' if y.startswith('Studies.') else 'theory'
        by_layer = collections.defaultdict(collections.Counter)
        for y in up:
            if y not in T['by_mod']: k = 'not measured'
            else:
                named, proof, carried = rests(y)
                k = 'names it' if m in named else 'has it carried' if m in carried else 'proofs only' if m in proof else 'only reaches it'
                if m in carried:
                    ch = carried[m]; via[T['names'][ch[1] if len(ch) > 1 else ch[0]]] += 1
            kind[k] += 1; by_layer[layer(y)][k] += 1
        print(f'{short(m)}: {len(up)} files rest on it')
        for k in ('names it', 'has it carried', 'proofs only', 'only reaches it', 'not measured'):
            if kind[k]: print(f'   {kind[k]:5d}  {k:16} ' + '  '.join(f'{L} {by_layer[L][k]}' for L in ('theory', 'Languages', 'Data', 'Studies') if by_layer[L][k]))
        if via:
            print('carried to them through:')
            for d, n in via.most_common(12): print(f'   {n:5d}  {d}')
    elif cmd == 'hot':
        G = imports(); c = closure(G); pre = ('Linglib.' + args[0] + '.') if args else None
        kids = collections.defaultdict(list)
        for x in G:
            p = x.split('.')
            if p[0] != 'Linglib' or len(p) < 4 or p[1] not in THEORY: continue
            if pre and not x.startswith(pre): continue
            depth = len(pre.split('.')) if pre else 3
            if len(p) > depth: kids['.'.join(p[:depth])].append(x)
        rows = []
        for d, fs in kids.items():
            S = set(fs); entry = collections.defaultdict(set)
            for x in fs:
                for t in G[x]:
                    if t not in S and area(t) in THEORY and area(t) != area(x): entry[t].add(x)
            us = [u for u in G if u not in S and c(u) & S]
            if not us or not entry: continue
            every = set().union(*entry.values())
            inh = sum(1 for u in us if c(u) & every)
            top = max(entry, key=lambda t: sum(1 for u in us if c(u) & entry[t]))
            rows.append((inh / len(us), inh, len(us), d, top, len(entry)))
        for sh, inh, us, d, top, n in sorted(rows, reverse=True)[:int(os.environ.get('TAPROOT_TOP', 15))]:
            print(f'{100 * sh:4.0f}%  {inh:4d} of {us:4d}  {short(d):40} most inherited: {short(top)}' + (f' (+{n - 1})' if n > 1 else ''))
    elif cmd == 'changed':
        old = load(args[0]); want = [a if a.startswith(('Linglib.', 'Studies.')) else 'Linglib.' + a for a in args[1:]]
        carrier = lambda tab, ch: tab['names'][ch[1] if len(ch) > 1 else ch[0]]
        rows = []
        for m in (want or sorted(set(T['by_mod']) & set(old['by_mod']))):
            if not m.startswith(('Linglib.', 'Studies.')) or m not in T['by_mod'] or m not in old['by_mod']: continue
            n1, _, c1 = rests(m); n0, _, c0 = rests(m, old)
            lib = lambda d: {x for x in d if x.startswith(('Linglib.', 'Studies.'))}
            newc, gone = lib(c1) - lib(c0), lib(c0) - lib(c1) - lib(n1)
            newn, unn = lib(n1) - lib(n0), lib(n0) - lib(n1)
            moved = {x for x in lib(c1) & lib(c0) if carrier(T, c1[x]) != carrier(old, c0[x])}
            if newc or gone or moved or (want and (newn or unn)): rows.append((len(newc) + len(gone), m, newc, gone, moved, newn, unn, c1, c0))
        print(f'{len(rows)} files differ in what is carried to them' + ('' if want else ' (files present in both tables)'))
        for _, m, newc, gone, moved, newn, unn, c1, c0 in sorted(rows, reverse=True)[:None if want else 30]:
            print(f'{short(m)}:  +{len(newc)} carried  -{len(gone)} no longer' + (f'  ~{len(moved)} carrier changed' if moved else ''))
            if want or len(rows) <= 12:
                for x in sorted(newc): print(f'      + {short(x)}  through {carrier(T, c1[x])}')
                for x in sorted(gone): print(f'      - {short(x)}  (was through {carrier(old, c0[x])})')
                for x in sorted(moved): print(f'      ~ {short(x)}  {carrier(old, c0[x])} -> {carrier(T, c1[x])}')
                if want:
                    for x in sorted(newn): print(f'      newly named: {short(x)}')
                    for x in sorted(unn): print(f'      no longer named: {short(x)}')
    elif cmd == 'slow':
        path, times = os.path.join(os.path.dirname(TABLE), 'times.tsv'), {}
        if os.path.exists(path):
            for line in open(path, encoding='utf-8'):
                m, _, sec = line.strip().partition('\t')
                if sec: times[m] = float(sec)
        if not times: sys.exit('no build times with this table: they are recorded only by a build that compiles the files')
        G = imports(); rev = collections.defaultdict(list)
        for x, ims in G.items():
            for i in ims: rev[i].append(x)
        def above(m):
            up, st = set(), [m]
            while st:
                for y in rev[st.pop()]:
                    if y not in up: up.add(y); st.append(y)
            return len(up)
        print(f'{len(times)} files timed, {sum(times.values()) / 60:.0f} minutes of compilation in all')
        for m, sec in sorted(times.items(), key=lambda kv: -kv[1])[:int(args[0]) if args else 15]:
            print(f'{sec:7.1f} s  {short(m):52} {above(m):4d} files wait on it')
    elif cmd == 'cut':
        m, i = (a if a.startswith(('Linglib.', 'Studies.')) else 'Linglib.' + a for a in args[:2])
        G = imports(); G2 = dict(G); G2[m] = [x for x in G[m] if x != i]
        only = ({i} | closure(G)(i)) - closure(G2)(m)
        need_it = [T['names'][k] for k in T['by_mod'].get(m, []) if '._' not in T['names'][k] and
                   any(T['mods'][d] in only for d in T['deps'][k])]
        print(f'{len(only)} files reach {short(m)} only through {short(i)}; its declarations that use them:')
        for n in sorted(need_it)[:20]: print('   ', n)
        simulate(G2, G, 'cut')
    elif cmd == 'move':
        new, decls = args[0], args[1:]
        new = new if new.startswith(('Linglib.', 'Studies.')) else 'Linglib.' + new
        G = imports(); G2 = {k: list(v) for k, v in G.items()}
        home = T['mods'][ids_of(decls[0])[0]]
        G2[new] = [home] + G[home]
        u = users(decls)
        print(f'{len(u)} files use the moved declarations and import {short(new)}:')
        for m in sorted(u):
            print('   ', short(m)); G2[m] = G2.get(m, []) + [new]
    else:
        print(__doc__)

if __name__ == '__main__':
    main(sys.argv[1:] or ['help'])
