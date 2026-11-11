"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const { games, validateCombinations } = require("../web/games.js");

test("provides the supported game configurations", () => {
  assert.deepEqual(Object.keys(games), [
    "power_6_55",
    "mega_6_45",
    "lotto_5_35",
    "bingo_18",
    "max_3d",
    "max_3d_pro",
    "keno",
  ]);
  assert.equal(games.power_6_55.count, 6);
  assert.equal(games.power_6_55.max, 55);
  assert.equal(games.mega_6_45.max, 45);
  assert.equal(games.lotto_5_35.count, 6);
  assert.equal(games.lotto_5_35.specialMax, 12);
  assert.equal(games.bingo_18.choices.length, 38);
  assert.equal(games.max_3d.kind, "three_digit");
  assert.equal(games.max_3d_pro.count, 2);
  assert.equal(games.keno.minCount, 1);
  assert.equal(games.keno.count, 10);
});

test("accepts a valid Power 6/55 combination and normalizes the legacy game id", () => {
  assert.deepEqual(
    validateCombinations("power_6_55", [["01", "09", "18", "27", "41", "55"]]),
    [],
  );
  assert.deepEqual(
    validateCombinations("mega_6_55", [["01", "09", "18", "27", "41", "55"]]),
    [],
  );
});

test("rejects Mega numbers outside the selected game's range", () => {
  assert.match(
    validateCombinations("mega_6_45", [["01", "09", "18", "27", "41", "46"]])[0],
    /from 1 to 45/,
  );
  assert.match(
    validateCombinations("power_6_55", [["00", "09", "18", "27", "41", "55"]])[0],
    /from 1 to 55/,
  );
});

test("rejects duplicate numbers in a Mega combination", () => {
  assert.match(
    validateCombinations("power_6_55", [["01", "09", "18", "27", "41", "01"]])[0],
    /duplicate numbers/,
  );
});

test("rejects a Mega combination with the wrong number of entries", () => {
  assert.match(
    validateCombinations("power_6_55", [["01", "09", "18"]])[0],
    /must contain 6 numbers/,
  );
});

test("validates Lotto 5/35 main and special numbers separately", () => {
  assert.deepEqual(
    validateCombinations("lotto_5_35", [["01", "09", "18", "27", "35", "09"]]),
    [],
  );
  assert.match(
    validateCombinations("lotto_5_35", [["01", "09", "18", "27", "36", "09"]])[0],
    /main numbers must be from 1 to 35/,
  );
  assert.match(
    validateCombinations("lotto_5_35", [["01", "09", "18", "27", "35", "13"]])[0],
    /special number must be from 1 to 12/,
  );
});

test("validates Bingo18 outcome selections", () => {
  assert.deepEqual(
    validateCombinations("bingo_18", [["number_3"], ["tie"], ["sum_18"], ["pair_3"], ["triple_6"], ["any_triple"]]),
    [],
  );
  assert.match(validateCombinations("bingo_18", [["sum_19"]])[0], /supported Bingo18 outcome/);
  assert.deepEqual(validateCombinations("bingo_18", [["even"], ["odd"]]), []);
});

test("accepts three-digit values including leading zeroes", () => {
  assert.deepEqual(validateCombinations("max_3d", [["000"], ["007"], ["999"]]), []);
});

test("rejects malformed three-digit values", () => {
  for (const value of ["7", "07", "1000", "abc"]) {
    assert.match(validateCombinations("max_3d", [[value]])[0], /three-digit number/);
  }
});

test("validates two Max 3D Pro numbers", () => {
  assert.deepEqual(validateCombinations("max_3d_pro", [["007", "123"]]), []);
  assert.match(validateCombinations("max_3d_pro", [["007"]])[0], /2 three-digit numbers/);
  assert.match(validateCombinations("max_3d_pro", [["007", "1000"]])[0], /three-digit numbers/);
});

test("validates Keno selections from one to ten unique numbers in range", () => {
  assert.deepEqual(validateCombinations("keno", [["01"]]), []);
  assert.deepEqual(validateCombinations("keno", [["01", "02", "03", "04", "05", "06", "07", "08", "09", "80"]]), []);
  assert.match(validateCombinations("keno", [[]])[0], /between 1 and 10/);
  assert.match(
    validateCombinations("keno", [["01", "01"]])[0],
    /duplicate numbers/,
  );
  assert.match(validateCombinations("keno", [["81"]])[0], /from 1 to 80/);
  assert.match(
    validateCombinations("keno", [["01", "02", "03", "04", "05", "06", "07", "08", "09", "10", "11"]])[0],
    /between 1 and 10/,
  );
});

test("requires at least one combination and a supported game", () => {
  assert.match(validateCombinations("max_3d", [])[0], /at least one/);
  assert.match(validateCombinations("unknown", [["123"]])[0], /supported game/);
});
