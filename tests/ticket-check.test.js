"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const { checkCombination, checkTicket, fetchDrawHistory, parseEventStream } = require("../web/ticket-check.js");

test("history lookup sends only the product ID and draw date", async () => {
  const calls = [];
  const fetchImpl = async (url, options = {}) => {
    calls.push({ url, options });
    if (calls.length === 1) {
      return { ok: true, json: async () => ({ event_id: "lookup-1" }) };
    }
    return {
      ok: true,
      text: async () => [
        "event: complete",
        `data: ${JSON.stringify({ data: [[{ draw_id: "123", draw_date: "2026-11-10" }]] })}`,
        "",
      ].join("\n"),
    };
  };

  const draws = await fetchDrawHistory("mega_6_45", "2026-11-10", fetchImpl);

  assert.deepEqual(draws, [{ draw_id: "123", draw_date: "2026-11-10" }]);
  assert.equal(calls.length, 2);
  assert.equal(calls[0].url, "/gradio_api/call/lookup_official_draws");
  assert.deepEqual(JSON.parse(calls[0].options.body), {
    data: ["mega_6_45", "2026-11-10"],
  });
  assert.deepEqual(Object.keys(JSON.parse(calls[0].options.body)), ["data"]);
  assert.equal(calls[1].url, "/gradio_api/call/lookup_official_draws/lookup-1");
  assert.equal(calls[1].options.body, undefined);
});

test("shares concurrent lookups for the same product and draw date", async () => {
  const calls = [];
  const fetchImpl = async (url, options = {}) => {
    calls.push({ url, options });
    if (calls.length === 1) {
      return { ok: true, json: async () => ({ event_id: "shared-lookup" }) };
    }
    return {
      ok: true,
      text: async () => `data: ${JSON.stringify({ data: [[{ draw_id: "456" }]] })}\n`,
    };
  };

  const histories = await Promise.all([
    fetchDrawHistory("power_6_55", "2026-11-11", fetchImpl),
    fetchDrawHistory("power_6_55", "2026-11-11", fetchImpl),
  ]);

  assert.deepEqual(histories[0], [{ draw_id: "456" }]);
  assert.deepEqual(histories[1], [{ draw_id: "456" }]);
  assert.equal(calls.length, 2);
});

test("rejects malformed or failed Gradio event responses explicitly", () => {
  assert.throws(() => parseEventStream("event: complete\ndata: not-json\n"), /invalid result response/);
  assert.throws(
    () => parseEventStream(`event: error\ndata: ${JSON.stringify({ error: "lookup failed" })}\n`),
    /lookup failed/,
  );
});

test("parses Gradio's output-wrapped draw-history response", () => {
  const draw = { draw_id: "789", draw_date: "2026-11-10" };
  assert.deepEqual(parseEventStream(`event: complete\ndata: ${JSON.stringify([[draw]])}\n`), [draw]);
});

test("parses explicit history lookup results and errors", () => {
  const draw = { draw_id: "789", draw_date: "2026-11-10" };
  assert.deepEqual(
    parseEventStream(`event: complete\ndata: ${JSON.stringify([{ draws: [draw], error: null }])}\n`),
    [draw],
  );
  assert.throws(
    () => parseEventStream(`event: complete\ndata: ${JSON.stringify([[{ draws: [], error: "Vietlott is unavailable." }]])}\n`),
    /Vietlott is unavailable/,
  );
  assert.throws(
    () => parseEventStream('event: error\ndata: {"error":null}\n'),
    /service returned an error without details/,
  );
});

test("matches Mega and Power tickets against main and special numbers", () => {
  const draw = {
    numbers: ["01", "09", "18", "27", "41", "55"],
    special: "39",
  };
  assert.equal(checkCombination("mega_6_45", ["01", "09", "18", "30", "31", "32"], draw), true);
  assert.equal(checkCombination("mega_6_45", ["01", "09", "30", "31", "32", "33"], draw), false);
  assert.equal(checkCombination("power_6_55", ["01", "09", "18", "27", "41", "39"], draw), true);
  assert.equal(checkCombination("power_6_55", ["01", "09", "30", "31", "32", "39"], draw), false);
});

test("keeps the uncertain Lotto 5/35 consolation case pending", () => {
  const draw = { numbers: ["01", "09", "18", "27", "35"], special: "12" };
  assert.equal(checkCombination("lotto_5_35", ["01", "09", "20", "21", "22", "12"], draw), null);
  assert.equal(checkCombination("lotto_5_35", ["01", "09", "18", "21", "22", "02"], draw), true);
  assert.equal(checkCombination("lotto_5_35", ["01", "02", "03", "04", "05", "06"], draw), false);
});

test("matches the official Bingo18 one-number, pair, triple, total, and size outcomes", () => {
  const draw = { numbers: ["3", "1", "1"], total: 5, size: "Small" };
  assert.equal(checkCombination("bingo_18", ["number_1"], draw), true);
  assert.equal(checkCombination("bingo_18", ["pair_1"], draw), true);
  assert.equal(checkCombination("bingo_18", ["triple_1"], draw), false);
  assert.equal(checkCombination("bingo_18", ["small"], draw), true);
  assert.equal(checkCombination("bingo_18", ["tie"], draw), false);
  assert.equal(checkCombination("bingo_18", ["sum_5"], draw), true);
  assert.equal(checkCombination("bingo_18", ["any_triple"], draw), false);
  assert.equal(checkCombination("bingo_18", ["odd"], draw), null);
});

test("matches Max 3D prizes and Max 3D Pro pair tiers without sending combinations", () => {
  const max3d = {
    prize_groups: [
      { prizes: [{ prize: "Special", numbers: ["123"] }, { prize: "First", numbers: ["456"] }] },
    ],
  };
  const max3dPro = {
    prize_groups: [{
      prizes: [
        { prize: "Special", numbers: ["123", "456"] },
        { prize: "First", numbers: ["111", "222", "333", "444"] },
        { prize: "Fifth", numbers: ["123", "456"] },
        { prize: "Sixth", numbers: ["555", "666"] },
      ],
    }],
  };
  assert.equal(checkCombination("max_3d", ["123"], max3d), true);
  assert.equal(checkCombination("max_3d", ["999"], max3d), false);
  assert.equal(checkCombination("max_3d_pro", ["111", "444"], max3dPro), true);
  assert.equal(checkCombination("max_3d_pro", ["123", "999"], max3dPro), true);
  assert.equal(checkCombination("max_3d_pro", ["777", "888"], max3dPro), false);
  assert.equal(checkCombination("max_3d_pro", ["777", "777"], max3dPro), null);
});

test("uses Vietlott's Keno payout table to distinguish winning and losing matches", () => {
  const draw = { numbers: ["01", "02", "03", "04", "05", "06", "07", "08", "09", "10"] };
  assert.equal(checkCombination("keno", ["01", "02", "12", "13", "14", "15"], draw), true);
  assert.equal(checkCombination("keno", ["01", "11"], draw), false);
  assert.equal(checkCombination("keno", ["11", "12", "13", "14", "15", "16", "17", "18", "19", "20"], draw), true);
  assert.equal(checkCombination("keno", ["11"], draw), false);
});

test("marks a ticket as won if any entered combination wins", () => {
  const draw = { numbers: ["01", "09", "18", "27", "41", "55"] };
  assert.equal(checkTicket("mega_6_45", [
    ["02", "03", "04", "05", "06", "07"],
    ["01", "09", "18", "30", "31", "32"],
  ], draw), "won");
});
