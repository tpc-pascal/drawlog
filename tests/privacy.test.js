"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

const root = path.join(__dirname, "..");

test("the app does not persist ticket data in browser storage or send it over the network", () => {
  const browserApis = ["localStorage", "sessionStorage", "XMLHttpRequest", "sendBeacon"];
  for (const file of fs.readdirSync(path.join(root, "web")).filter((name) => name.endsWith(".js"))) {
    const source = fs.readFileSync(path.join(root, "web", file), "utf8");
    for (const api of browserApis) {
      assert.equal(source.includes(api), false, `${file} uses browser data API: ${api}`);
    }
    if (file !== "ticket-check.js") {
      assert.doesNotMatch(source, /\bfetch(?:Impl)?\s*\(/, `${file} sends a network request`);
    }
  }
});

test("the static app loads local scripts and has no form upload target", () => {
  const html = fs.readFileSync(path.join(root, "index.html"), "utf8");
  assert.match(html, /<input id="csv-file" type="file" accept="\.csv,text\/csv" hidden>/);
  assert.match(html, /<script src="web\/latest-results\.js" defer><\/script>/);
  assert.match(html, /<script src="web\/ticket-check\.js" defer><\/script>/);
  assert.match(html, /id="draw-id"/);
  assert.match(html, /id="latest-results-list"/);
  assert.doesNotMatch(html, /<form[^>]+\baction\s*=/i);
  assert.doesNotMatch(html, /<(?:script|link)[^>]+https?:\/\//i);
});

test("the ledger layout stays compact and adapts to narrow screens", () => {
  const html = fs.readFileSync(path.join(root, "index.html"), "utf8");
  const styles = fs.readFileSync(path.join(root, "web", "styles.css"), "utf8");

  assert.match(html, /<h1 id="page-title">Ticket ledger<\/h1>/);
  assert.match(styles, /body > main, #drawlog-app > main \{ width: min\(920px, calc\(100% - 40px\)\)/);
  assert.match(styles, /\.main-tabs \{/);
  assert.match(styles, /@media \(max-width: 760px\)/);
  assert.match(styles, /@media \(max-width: 520px\)/);
});

test("the main sections are presented as accessible tabs", () => {
  const html = fs.readFileSync(path.join(root, "index.html"), "utf8");
  const tabs = [
    ["entry-tab", "entry-panel"],
    ["results-tab", "results-panel"],
    ["tickets-tab", "tickets-panel"],
  ];

  assert.match(html, /role="tablist" aria-label="Drawlog sections"/);
  for (const [tabId, panelId] of tabs) {
    assert.match(html, new RegExp(`id="${tabId}"[^>]*role="tab"[^>]*aria-controls="${panelId}"`));
    assert.match(html, new RegExp(`<section id="${panelId}"[^>]*role="tabpanel"`));
    assert.match(html, new RegExp(`aria-labelledby="${tabId}"`));
  }
  assert.match(html, /id="entry-tab"[^>]*aria-selected="true"/);
  assert.match(html, /id="results-panel"[^>]*hidden/);
  assert.match(html, /id="tickets-panel"[^>]*hidden/);
  assert.match(html, /id="entry-panel"[^>]*role="tabpanel"/);
  assert.ok(html.indexOf('id="entry-tab"') < html.indexOf('id="results-tab"'));
  assert.ok(html.indexOf('id="results-tab"') < html.indexOf('id="tickets-tab"'));
});
