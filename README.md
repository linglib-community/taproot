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
python3 lib/map.py --out OUT.html [--base DIR] [--groups FILE]    # the zoomable map, one page
bin/tap map [ADDRESS]                                           # the map from the newest nightly table, opened
```

`OUT` holds `index.html`, `graph.json` and, where scikit-learn is installed, `landscape.json`.

## Parts

- `lib/Extract.lean`: loads the compiled modules and writes, per declaration, what its statement and
  its body depend on.
- `lib/analyze.py`: turns that table into the measures of the page (`graph.json`).
- `lib/landscape.py`: places every hand-written file near the files its declarations use, with its
  exposure and review priority (`landscape.json`).
- `lib/page.html`: the page.
- `lib/query.py`: questions to the table (`users`, `needs`, `cut`, `move`; `cone` and `why` say
  what a file names and what is carried to it through which declaration; `roots` lists directories
  whose root files import another theory area).
- `lib/map.py`, `lib/map.html`: the map. Areas, then directories, then files as islands of dots,
  coloured by what is being looked for; a file opens as its whole descent to mathlib, or as what
  rests on it. Every view has an address, so it can be opened at one place with a note.
- `lib/groups.py`: what the map knows that imports do not say: language families, from the checkout's
  WALS table, and the layout of the theory areas.
- `lib/ci_map.sh`: the one line linglib's nightly workflow runs to build the published page.
- `lib/test_map.sh`: opens a built page in headless Chrome and checks its views and gestures.
- `bin/tap`: one command for all of it against the newest nightly table, kept in `~/.cache/taproot`
  (`tap up FILE`, `tap why A B`, `tap hot`, `tap changed`, `tap map ADDRESS`, `tap test`,
  `tap measure FILE...` for a branch). `tap help` lists them.
- `mcp_server.py`: the same questions as MCP tools; `claude mcp add taproot -- python3 PATH/mcp_server.py`.
