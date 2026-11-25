# tendril

Tooling for the dependency map of [linglib](https://github.com/linglib-community/linglib): for every
theorem of a study, the declarations its statement rests on, traced back to mathlib.

## Use

Run from a linglib checkout, or set `LINGLIB_ROOT` to one.

```bash
python3 gen_tendrils.py                         # after `lake build`: extract, analyse, write the page
python3 gen_tendrils.py --extract-only DIR      # only the declaration table (the nightly build uploads it)
python3 gen_tendrils.py --from-table DIR --out OUT   # the page from a downloaded table
TENDRILS_TABLE=DIR/table.tsv python3 tendrils/query.py users DECL
```

`OUT` holds `index.html`, `graph.json` and, where scikit-learn is installed, `landscape.json`.

## Parts

- `tendrils/Extract.lean`: loads the compiled modules and writes, per declaration, what its
  statement and its body depend on.
- `tendrils/analyze.py`: turns that table into the measures of the page (`graph.json`).
- `tendrils/landscape.py`: places every hand-written file near the files its declarations use,
  with its exposure and suspicion (`landscape.json`).
- `tendrils/page.html`: the page.
- `tendrils/query.py`: questions to the table (`users`, `needs`, `cut`, `move`).

linglib keeps its own copy of the extractor for the nightly table.
