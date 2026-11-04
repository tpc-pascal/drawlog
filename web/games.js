(function (root) {
  "use strict";

  const games = {
    mega_6_55: {
      label: "Mega 6/55",
      kind: "lotto",
      count: 6,
      min: 1,
      max: 55,
      hint: "Choose 6 different numbers from 01 to 55.",
    },
    mega_6_45: {
      label: "Mega 6/45",
      kind: "lotto",
      count: 6,
      min: 1,
      max: 45,
      hint: "Choose 6 different numbers from 01 to 45.",
    },
    max_3d: {
      label: "Max 3D",
      kind: "three_digit",
      count: 1,
      hint: "Enter a three-digit number from 000 to 999.",
    },
  };

  function validateCombinations(gameId, combinations) {
    const game = games[gameId];
    if (!game) return ["Select a supported game type."];
    if (!Array.isArray(combinations) || combinations.length === 0) {
      return ["Add at least one number combination."];
    }

    const errors = [];
    combinations.forEach((combination, index) => {
      const label = `Combination ${index + 1}`;
      if (!Array.isArray(combination) || combination.length !== game.count) {
        errors.push(`${label} must contain ${game.count} number${game.count === 1 ? "" : "s"}.`);
        return;
      }

      if (game.kind === "three_digit") {
        if (!/^\d{3}$/.test(String(combination[0]))) {
          errors.push(`${label} must be a three-digit number from 000 to 999.`);
        }
        return;
      }

      const values = combination.map((value) => {
        const text = String(value).trim();
        return /^\d+$/.test(text) ? Number(text) : Number.NaN;
      });
      if (values.some((value) => !Number.isInteger(value) || value < game.min || value > game.max)) {
        errors.push(`${label} numbers must be from ${game.min} to ${game.max}.`);
      }
      if (new Set(values).size !== values.length) {
        errors.push(`${label} cannot contain duplicate numbers.`);
      }
    });
    return errors;
  }

  const api = { games, validateCombinations };
  root.DrawlogGames = api;
  if (typeof module !== "undefined" && module.exports) module.exports = api;
})(globalThis);
