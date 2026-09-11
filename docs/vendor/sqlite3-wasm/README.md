Vendored from the official `@sqlite.org/sqlite-wasm` npm package
(version 3.53.0-build1, Apache-2.0 licensed; SQLite itself is public
domain). Copied by hand -- no npm/Node involved in this project's own
build -- from `dist/index.mjs` and `dist/sqlite3.wasm` of that package.

Only the plain "main thread, in-memory" build is used (this site
downloads the whole `lahu-dictionary.sqlite3` file once and keeps it in
memory via `sqlite3_deserialize`; see docs/app.js). The worker/OPFS
files that ship in the same package (`sqlite3-worker1.mjs`,
`sqlite3-opfs-async-proxy.js`) aren't needed and weren't copied.

To update: fetch a newer version of the same two files from
https://www.npmjs.com/package/@sqlite.org/sqlite-wasm (e.g. via
unpkg.com/@sqlite.org/sqlite-wasm/dist/index.mjs and
.../dist/sqlite3.wasm) and replace both files here.
