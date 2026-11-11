"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
require("../web/games.js");
const { parseRows, parseTickets, stringifyTickets } = require("../web/csv.js");

const header = "game,purchase_date,draw_date,combinations,paid,prize,result,note";

test("parses quoted CSV fields, escaped quotes, CRLF, and a UTF-8 BOM", () => {
  assert.deepEqual(
    parseRows(`\uFEFFa,b,c\r\n1,"two, too","say ""hi"""\r\n`),
    [["a", "b", "c"], ["1", "two, too", 'say "hi"']],
  );
});

test("imports valid tickets with flexible column order and optional notes", () => {
  const tickets = parseTickets(
    "result,game,draw_date,combinations,paid,purchase_date,prize\r\n" +
      "won,Power 6/55,2026-11-12,01 09 18 27 41 55,10000,09/11/2026,50000\r\n",
  );
  assert.deepEqual(tickets, [{
    game: "power_6_55",
    purchaseDate: "2026-11-09",
    drawDate: "2026-11-12",
    combinations: [["01", "09", "18", "27", "41", "55"]],
    drawId: "",
    paid: 10000,
    prize: 50000,
    result: "won",
    note: "",
  }]);
});

test("round-trips exported tickets including commas, quotes, and line breaks", () => {
  const tickets = parseTickets(`${header}\npower_6_55,2026-11-09,2026-11-12,"01 09 18 27 41 55",10000,0,pending,"shop, ""A""\nwindow"`);
  assert.deepEqual(parseTickets(stringifyTickets(tickets)), tickets);
});

test("imports historical Mega 6/55 ids and labels as Power 6/55", () => {
  for (const game of ["mega_6_55", "Mega 6/55"]) {
    const ticket = parseTickets(
      `${header}\n${game},2026-11-09,2026-11-12,"01 09 18 27 41 55",10000,0,pending,`,
    )[0];
    assert.equal(ticket.game, "power_6_55");
  }
});

test("imports each supported product's combination format", () => {
  const tickets = parseTickets(
    `${header}\n` +
      `lotto_5_35,2026-11-09,2026-11-12,"01 09 18 27 35 12",10000,0,pending,\n` +
      `bingo_18,2026-11-09,2026-11-12,big,10000,0,pending,\n` +
      `max_3d_pro,2026-11-09,2026-11-12,"007 123",10000,0,pending,\n` +
      `keno,2026-11-09,2026-11-12,"01 08 80",10000,0,pending,`,
  );
  assert.deepEqual(tickets.map(({ game, combinations }) => [game, combinations]), [
    ["lotto_5_35", [["01", "09", "18", "27", "35", "12"]]],
    ["bingo_18", [["big"]]],
    ["max_3d_pro", [["007", "123"]]],
    ["keno", [["01", "08", "80"]]],
  ]);
  assert.deepEqual(parseTickets(stringifyTickets(tickets)), tickets);
});

test("imports and exports an optional draw number while accepting older CSV files", () => {
  const withDrawId = parseTickets(
    `${header},draw_id\n` +
      `bingo_18,2026-11-09,2026-11-09,number_3,10000,0,pending,,0195579`,
  );
  assert.equal(withDrawId[0].drawId, "0195579");
  assert.deepEqual(parseTickets(stringifyTickets(withDrawId)), withDrawId);
  assert.equal(parseTickets(`${header}\nmega_6_45,2026-11-09,2026-11-12,"01 09 18 27 41 45",10000,0,pending,`)[0].drawId, "");
  assert.throws(
    () => parseTickets(`${header},draw_id\nmega_6_45,2026-11-09,2026-11-12,"01 09 18 27 41 45",10000,0,pending,,abc`),
    /draw_id must contain 1 to 12 digits/,
  );
});

test("rejects malformed CSV quoting and invalid columns", () => {
  assert.throws(() => parseRows('a,"unfinished'), /unclosed quoted field/);
  assert.throws(() => parseTickets("game,paid\nmega_6_55,10000"), /columns are invalid/);
});

test("rejects malformed ticket data before returning imported records", () => {
  assert.throws(
    () => parseTickets(`${header}\nmega_6_45,2026-11-09,2026-11-12,"01 09 18 27 41 46",10000,0,pending,`),
    /Row 2: Combination 1 numbers must be from 1 to 45/,
  );
  assert.throws(
    () => parseTickets(`${header}\nmax_3d,2026-11-12,2026-11-09,007,10000,0,pending,`),
    /draw_date cannot be earlier/,
  );
});

test("protects exported notes from spreadsheet formula execution", () => {
  const csv = stringifyTickets([{
    game: "power_6_55",
    purchaseDate: "2026-11-09",
    drawDate: "2026-11-12",
    combinations: [["01", "09", "18", "27", "41", "55"]],
    paid: 10000,
    prize: 0,
    result: "pending",
    note: " =1+1",
  }]);
  assert.match(csv, /"' =1\+1"/);
});
