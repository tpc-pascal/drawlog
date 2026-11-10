"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const { games, validateCombinations } = require("../web/games.js");

test("provides the supported game configurations", () => {
  assert.deepEqual(Object.keys(games), ["mega_6_55", "mega_6_45", "max_3d"]);
  assert.equal(games.mega_6_55.count, 6);
  assert.equal(games.mega_6_55.max, 55);
  assert.equal(games.mega_6_45.max, 45);
  assert.equal(games.max_3d.kind, "three_digit");
});

test("accepts a valid Mega 6/55 combination", () => {
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
    validateCombinations("mega_6_55", [["00", "09", "18", "27", "41", "55"]])[0],
    /from 1 to 55/,
  );
});

test("rejects duplicate numbers in a Mega combination", () => {
  assert.match(
    validateCombinations("mega_6_55", [["01", "09", "18", "27", "41", "01"]])[0],
    /duplicate numbers/,
  );
});

test("rejects a Mega combination with the wrong number of entries", () => {
  assert.match(
    validateCombinations("mega_6_55", [["01", "09", "18"]])[0],
    /must contain 6 numbers/,
  );
});

test("accepts three-digit values including leading zeroes", () => {
  assert.deepEqual(validateCombinations("max_3d", [["000"], ["007"], ["999"]]), []);
});

test("rejects malformed three-digit values", () => {
  for (const value of ["7", "07", "1000", "abc"]) {
    assert.match(validateCombinations("max_3d", [[value]])[0], /three-digit number/);
  }
});

test("requires at least one combination and a supported game", () => {
  assert.match(validateCombinations("max_3d", [])[0], /at least one/);
  assert.match(validateCombinations("unknown", [["123"]])[0], /supported game/);
});
