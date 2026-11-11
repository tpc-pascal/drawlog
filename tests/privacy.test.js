"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

const root = path.join(__dirname, "..");

test("the app does not persist ticket data in browser storage or send it over the network", () => {
  const browserApis = ["localStorage", "sessionStorage", "fetch(", "XMLHttpRequest", "sendBeacon"];
  for (const file of fs.readdirSync(path.join(root, "web")).filter((name) => name.endsWith(".js"))) {
    const source = fs.readFileSync(path.join(root, "web", file), "utf8");
    for (const api of browserApis) {
      assert.equal(source.includes(api), false, `${file} uses browser data API: ${api}`);
    }
  }
});

test("the static app loads local scripts and has no form upload target", () => {
  const html = fs.readFileSync(path.join(root, "index.html"), "utf8");
  assert.match(html, /<input id="csv-file" type="file" accept="\.csv,text\/csv" hidden>/);
  assert.match(html, /<script src="web\/latest-results\.js" defer><\/script>/);
  assert.match(html, /id="latest-results-list"/);
  assert.doesNotMatch(html, /<form[^>]+\baction\s*=/i);
  assert.doesNotMatch(html, /<(?:script|link)[^>]+https?:\/\//i);
});

test("the ledger layout stays compact and adapts to narrow screens", () => {
  const html = fs.readFileSync(path.join(root, "index.html"), "utf8");
  const styles = fs.readFileSync(path.join(root, "web", "styles.css"), "utf8");

  assert.match(html, /<h1 id="page-title">Ticket ledger<\/h1>/);
  assert.match(styles, /body > main, #drawlog-app > main \{ width: min\(920px, calc\(100% - 40px\)\)/);
  assert.match(styles, /\.workspace \{ display: grid; grid-template-columns: repeat\(2, minmax\(0, 1fr\)\)/);
  assert.match(styles, /@media \(max-width: 760px\)/);
  assert.match(styles, /@media \(max-width: 520px\)/);
});
