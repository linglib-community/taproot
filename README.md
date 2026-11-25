# taproot

Tooling for the dependency map of [linglib](https://github.com/linglib-community/linglib): for every
theorem of a study, the declarations its statement rests on, traced down to mathlib. A claim whose
trace never enters the shared library stops in its own file.

## Use

Run from a linglib checkout, or set `LINGLIB_ROOT` to one.

```bash
python3 taproot.py                              # after `lake build`: extract, analyse, write the page
python3 taproot.py --extract-only DIR           # only the declaration table (the nightly build uploads it)
python3 taproot.py --from-table DIR --out OUT   # the page from a downloaded table
TAPROOT_TABLE=DIR/table.tsv python3 lib/query.py users DECL
```

`OUT` holds `index.html`, `graph.json` and, where scikit-learn is installed, `landscape.json`.

## Parts

- `lib/Extract.lean`: loads the compiled modules and writes, per declaration, what its statement and
  its body depend on.
- `lib/analyze.py`: turns that table into the measures of the page (`graph.json`).
- `lib/landscape.py`: places every hand-written file near the files its declarations use, with its
  exposure and review priority (`landscape.json`).
- `lib/page.html`: the page.
- `lib/query.py`: questions to the table (`users`, `needs`, `cut`, `move`).
