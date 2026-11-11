(function (root) {
  "use strict";

  const bingo18Choices = [
    { value: "big", label: "Big" },
    { value: "small", label: "Small" },
    { value: "even", label: "Even" },
    { value: "odd", label: "Odd" },
    ...Array.from({ length: 16 }, (_, index) => {
      const total = index + 3;
      return { value: `sum_${total}`, label: `Total ${total}` };
    }),
    ...Array.from({ length: 6 }, (_, index) => {
      const number = index + 1;
      return { value: `pair_${number}`, label: `Pair ${number}${number}` };
    }),
    ...Array.from({ length: 6 }, (_, index) => {
      const number = index + 1;
      return { value: `triple_${number}`, label: `Triple ${number}${number}${number}` };
    }),
  ];

  const games = {
    power_6_55: {
      label: "Power 6/55",
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
    lotto_5_35: {
      label: "Lotto 5/35",
      kind: "lotto_special",
      count: 6,
      mainCount: 5,
      min: 1,
      max: 35,
      specialMin: 1,
      specialMax: 12,
      hint: "Choose 5 different numbers from 01 to 35 and 1 special number from 01 to 12.",
    },
    bingo_18: {
      label: "Bingo18",
      kind: "bingo18",
      choices: bingo18Choices,
      hint: "Choose a Bingo18 outcome: size, parity, total, pair, or triple.",
    },
    max_3d: {
      label: "Max 3D",
      kind: "three_digit",
      count: 1,
      hint: "Enter a three-digit number from 000 to 999.",
    },
    max_3d_pro: {
      label: "Max 3D Pro",
      kind: "three_digit_pair",
      count: 2,
      hint: "Enter two three-digit numbers from 000 to 999.",
    },
    keno: {
      label: "Keno",
      kind: "keno",
      count: 10,
      minCount: 1,
      min: 1,
      max: 80,
      hint: "Choose 1 to 10 different numbers from 01 to 80.",
    },
  };

  const aliases = {
    mega_6_55: "power_6_55",
    "mega 6/55": "power_6_55",
  };

  function normalizeGameId(value) {
    const normalized = String(value).trim().toLowerCase();
    return aliases[normalized] || normalized;
  }

  function validateCombinations(gameId, combinations) {
    const game = games[normalizeGameId(gameId)];
    if (!game) return ["Select a supported game type."];
    if (!Array.isArray(combinations) || combinations.length === 0) {
      return ["Add at least one number combination."];
    }

    const errors = [];
    combinations.forEach((combination, index) => {
      const label = `Combination ${index + 1}`;
      if (!Array.isArray(combination)) {
        errors.push(`${label} must contain valid selections.`);
        return;
      }

      if (game.kind === "bingo18") {
        if (combination.length !== 1 || !game.choices.some((choice) => choice.value === combination[0])) {
          errors.push(`${label} must be a supported Bingo18 outcome.`);
        }
        return;
      }

      if (game.kind === "three_digit" || game.kind === "three_digit_pair") {
        if (
          combination.length !== game.count ||
          combination.some((value) => !/^\d{3}$/.test(String(value)))
        ) {
          errors.push(
            `${label} must contain ${game.count} three-digit number${game.count === 1 ? "" : "s"} from 000 to 999.`,
          );
        }
        return;
      }

      if (game.kind === "lotto_special") {
        if (combination.length !== game.count) {
          errors.push(`${label} must contain 5 main numbers and 1 special number.`);
          return;
        }
        const mainValues = combination.slice(0, game.mainCount).map(parseNumber);
        const specialValue = parseNumber(combination[game.mainCount]);
        if (mainValues.some((value) => !inRange(value, game.min, game.max))) {
          errors.push(`${label} main numbers must be from ${game.min} to ${game.max}.`);
        }
        if (new Set(mainValues).size !== mainValues.length) {
          errors.push(`${label} main numbers cannot contain duplicates.`);
        }
        if (!inRange(specialValue, game.specialMin, game.specialMax)) {
          errors.push(`${label} special number must be from ${game.specialMin} to ${game.specialMax}.`);
        }
        return;
      }

      const values = combination.map(parseNumber);
      if (game.kind === "keno") {
        if (values.length < game.minCount || values.length > game.count) {
          errors.push(`${label} must contain between ${game.minCount} and ${game.count} numbers.`);
          return;
        }
      } else if (values.length !== game.count) {
        errors.push(`${label} must contain ${game.count} numbers.`);
        return;
      }

      if (values.some((value) => !inRange(value, game.min, game.max))) {
        errors.push(`${label} numbers must be from ${game.min} to ${game.max}.`);
      }
      if (new Set(values).size !== values.length) {
        errors.push(`${label} cannot contain duplicate numbers.`);
      }
    });
    return errors;
  }

  function parseNumber(value) {
    const text = String(value).trim();
    return /^\d+$/.test(text) ? Number(text) : Number.NaN;
  }

  function inRange(value, min, max) {
    return Number.isInteger(value) && value >= min && value <= max;
  }

  const api = { games, normalizeGameId, validateCombinations };
  root.DrawlogGames = api;
  if (typeof module !== "undefined" && module.exports) module.exports = api;
})(globalThis);
