Vendored from the official `@sqlite.org/sqlite-wasm` npm package
(version 3.53.0-build1, Apache-2.0 licensed; SQLite itself is public
domain). Copied by hand -- no npm/Node involved in this project's own
build -- from `dist/index.mjs` and `dist/sqlite3.wasm` of that package.

Only the plain "main thread, in-memory" build is used (this site
downloads the whole `lahu-dictionary.sqlite3` file once and keeps it in
memory via `sqlite3_deserialize`; see docs/app.js). The worker/OPFS
files that ship in the same package (`sqlite3-worker1.mjs`,
`sqlite3-opfs-async-proxy.js`) aren't needed and weren't copied.

Deliberately placed at `docs/lib/sqlite3-wasm/`, not `docs/vendor/...`:
some shared-hosting Apache setups (including the project owner's own
EC2 box) blanket-deny any path containing `/vendor/` as a hardening
rule against accidentally exposing PHP/Composer or npm dependency
trees. That rule doesn't care that this vendor/ was hand-placed rather
than `npm install`-ed -- it 403's the path either way, and a browser
refuses to run a JS module served as an HTML error page ("disallowed
MIME type"). If you ever rename this folder back to `vendor/`, check
your server doesn't have that rule first.

To update: fetch a newer version of the same two files from
https://www.npmjs.com/package/@sqlite.org/sqlite-wasm (e.g. via
unpkg.com/@sqlite.org/sqlite-wasm/dist/index.mjs and
.../dist/sqlite3.wasm) and replace both files here.
