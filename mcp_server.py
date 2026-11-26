#!/usr/bin/env python3
"""The dependency table of a linglib checkout, as tools for an assistant.

    python3 mcp_server.py        # speaks MCP over stdio

Each tool runs `bin/tap`, so it reads the newest nightly table, fetched on first use and kept in
`~/.cache/taproot`, and every answer starts with which commit the table is from and how far behind
`origin/main` it is. The checkout is `LINGLIB_CHECKOUT`, or the directory the server is started in.

Register it once, from the checkout:

    claude mcp add taproot -- python3 /path/to/taproot/mcp_server.py
"""
import os, subprocess
from mcp.server.fastmcp import FastMCP

HERE = os.path.dirname(os.path.abspath(__file__))
TAP = os.path.join(HERE, 'bin', 'tap')
mcp = FastMCP('taproot')


def tap(*args, limit=12000):
    env = dict(os.environ)
    env.setdefault('LINGLIB_CHECKOUT', os.getcwd())
    r = subprocess.run([TAP, *[a for a in args if a]], capture_output=True, text=True, env=env, timeout=600)
    out = (r.stderr.strip() + '\n' if r.stderr.strip() else '') + r.stdout
    if r.returncode and not r.stdout: out += f'\n(tap exited {r.returncode})'
    return out if len(out) <= limit else out[:limit] + f'\n… {len(out) - limit} more characters; narrow the question'


@mcp.tool()
def rests_on_it(file: str) -> str:
    """What rests on a file: how many files, and of those how many name something in it, how many
    have it carried to them without naming it, and how many only reach it; by layer, with the
    declarations that carry it. Use before changing a file. `file` is dotted, e.g. Morphology.Morph."""
    return tap('up', file)


@mcp.tool()
def what_it_rests_on(file: str) -> str:
    """For one file, every file it imports sorted into: named by one of its own statements, carried
    to it through a declaration in between (which one), used in proofs only, or imported and unused."""
    return tap('cone', file)


@mcp.tool()
def why(file: str, target: str) -> str:
    """The chain of declarations by which `file` comes to rest on `target`, or that it names it itself."""
    return tap('why', file, target)


@mcp.tool()
def hot_spots(directory: str = '', top: int = 15) -> str:
    """Directories ranked by the share of the files using them that inherit a file from another
    theory area through them, with the most inherited file. `directory` narrows to one area, e.g. Syntax."""
    os.environ['TAPROOT_TOP'] = str(top)
    return tap('hot', directory)


@mcp.tool()
def root_crossings(top: int = 30) -> str:
    """Directories whose root files import another theory area, by how many of their users inherit it."""
    return tap('roots', str(top))


@mcp.tool()
def users(declarations: list[str]) -> str:
    """Files whose declarations mention any of these declarations, or anything under them."""
    return tap('users', *declarations)


@mcp.tool()
def needs(file: str) -> str:
    """What a file imports against what its declarations actually use."""
    return tap('needs', file)


@mcp.tool()
def changed(files: list[str] | None = None) -> str:
    """Against the nightly before this one: for each file, what is newly carried to it, what no longer
    is, and where the carrying declaration changed. With `files`, full detail for those files."""
    return tap('changed', *(files or []))


@mcp.tool()
def slowest(top: int = 15) -> str:
    """The files that took longest to build in the last clean build, with how many files wait on each."""
    return tap('slow', str(top))


@mcp.tool()
def cut_import(file: str, imported: str) -> str:
    """Simulate removing one import line from `file`: who would lose something they use."""
    return tap('cut', file, imported)


@mcp.tool()
def refresh() -> str:
    """Fetch the newest nightly table if it is not already cached, and say which commit it is from."""
    return tap('refresh')


@mcp.tool()
def show(address: str = '') -> str:
    """Build the map page and open it in the user's browser at an address, so they see what you are
    looking at. Addresses: '' the top map; 'm/Syntax.Feature' a map; 'f/Dotted.File' a file's descent;
    'f/Dotted.File?up=1' what rests on it; 'd/Dotted.Dir?vs=1' before and after. Append
    '&note=…' (or '?note=…') for a one-line caption and 'hl=A,B' to ring things."""
    return tap('map', address)


if __name__ == '__main__':
    mcp.run()
