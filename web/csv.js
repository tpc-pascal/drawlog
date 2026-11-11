(function (root) {
  "use strict";

  const { games, normalizeGameId, validateCombinations } = root.DrawlogGames;
  const headers = ["game", "purchase_date", "draw_date", "draw_id", "combinations", "paid", "prize", "result", "note"];
  const requiredHeaders = headers.filter((header) => header !== "note" && header !== "draw_id");
  const results = new Set(["pending", "no_prize", "won"]);

  function parseRows(text) {
    if (typeof text !== "string") throw new Error("CSV content must be text.");
    const source = text.replace(/^\uFEFF/, "");
    const rows = [];
    let row = [];
    let field = "";
    let quoted = false;
    let closedQuote = false;

    for (let index = 0; index < source.length; index += 1) {
      const character = source[index];
      if (quoted) {
        if (character === '"') {
          if (source[index + 1] === '"') {
            field += '"';
            index += 1;
          } else {
            quoted = false;
            closedQuote = true;
          }
        } else {
          field += character;
        }
        continue;
      }

      if (closedQuote) {
        if (character === ",") {
          row.push(field);
          field = "";
          closedQuote = false;
        } else if (character === "\n" || character === "\r") {
          row.push(field);
          rows.push(row);
          row = [];
          field = "";
          closedQuote = false;
          if (character === "\r" && source[index + 1] === "\n") index += 1;
        } else if (character !== " " && character !== "\t") {
          throw new Error(`Unexpected character after a quoted CSV field at character ${index + 1}.`);
        }
        continue;
      }

      if (character === '"') {
        if (field.trim() !== "") {
          throw new Error(`Unexpected quote in an unquoted CSV field at character ${index + 1}.`);
        }
        field = "";
        quoted = true;
      } else if (character === ",") {
        row.push(field);
        field = "";
      } else if (character === "\n" || character === "\r") {
        row.push(field);
        rows.push(row);
        row = [];
        field = "";
        if (character === "\r" && source[index + 1] === "\n") index += 1;
      } else {
        field += character;
      }
    }

    if (quoted) throw new Error("CSV contains an unclosed quoted field.");
    if (field !== "" || row.length > 0) {
      row.push(field);
      rows.push(row);
    }
    return rows;
  }

  function normalizeDate(value, rowNumber, fieldName) {
    const text = value.trim();
    let match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(text);
    if (!match) {
      match = /^(\d{2})\/(\d{2})\/(\d{4})$/.exec(text);
      if (match) match = [match[0], match[3], match[2], match[1]];
    }
    if (!match) throw new Error(`Row ${rowNumber}: ${fieldName} must use YYYY-MM-DD or DD/MM/YYYY.`);

    const [, yearText, monthText, dayText] = match;
    const year = Number(yearText);
    const month = Number(monthText);
    const day = Number(dayText);
    const date = new Date(Date.UTC(year, month - 1, day));
    if (
      date.getUTCFullYear() !== year ||
      date.getUTCMonth() !== month - 1 ||
      date.getUTCDate() !== day
    ) {
      throw new Error(`Row ${rowNumber}: ${fieldName} is not a valid date.`);
    }
    return `${yearText}-${monthText}-${dayText}`;
  }

  function parseGame(value, rowNumber) {
    const normalized = value.trim().toLowerCase();
    const gameId = normalizeGameId(normalized);
    if (games[gameId]) return gameId;
    const match = Object.entries(games).find(([, game]) => game.label.toLowerCase() === normalized);
    if (!match) throw new Error(`Row ${rowNumber}: unsupported game "${value}".`);
    return match[0];
  }

  function parseCombinations(value, game, rowNumber) {
    const combinations = value.trim().split(";").map((combination) =>
      combination.trim().split(/[\s,|]+/).filter(Boolean),
    );
    const errors = validateCombinations(game, combinations);
    if (errors.length) throw new Error(`Row ${rowNumber}: ${errors[0]}`);
    return combinations;
  }

  function parseAmount(value, fieldName, rowNumber) {
    const text = value.trim();
    if (!/^\d+$/.test(text)) throw new Error(`Row ${rowNumber}: ${fieldName} must be a whole non-negative VND amount.`);
    const amount = Number(text);
    if (!Number.isSafeInteger(amount)) throw new Error(`Row ${rowNumber}: ${fieldName} is too large.`);
    return amount;
  }

  function parseTickets(text) {
    const rows = parseRows(text).filter((row) => row.some((field) => field.trim() !== ""));
    if (rows.length < 2) throw new Error("CSV must contain a header row and at least one ticket.");

    const normalizedHeaders = rows[0].map((header) => header.trim().toLowerCase());
    if (new Set(normalizedHeaders).size !== normalizedHeaders.length) {
      throw new Error("CSV contains duplicate column names.");
    }
    const unknownHeaders = normalizedHeaders.filter((header) => !headers.includes(header));
    const missingHeaders = requiredHeaders.filter((header) => !normalizedHeaders.includes(header));
    if (unknownHeaders.length || missingHeaders.length) {
      const details = [];
      if (missingHeaders.length) details.push(`missing ${missingHeaders.join(", ")}`);
      if (unknownHeaders.length) details.push(`unsupported ${unknownHeaders.join(", ")}`);
      throw new Error(`CSV columns are invalid: ${details.join("; ")}.`);
    }

    const column = Object.fromEntries(normalizedHeaders.map((header, index) => [header, index]));
    const imported = [];
    for (let index = 1; index < rows.length; index += 1) {
      const row = rows[index];
      const rowNumber = index + 1;
      if (row.length !== normalizedHeaders.length) {
        throw new Error(`Row ${rowNumber}: expected ${normalizedHeaders.length} columns but found ${row.length}.`);
      }

      const game = parseGame(row[column.game], rowNumber);
      const purchaseDate = normalizeDate(row[column.purchase_date], rowNumber, "purchase_date");
      const drawDate = normalizeDate(row[column.draw_date], rowNumber, "draw_date");
      if (drawDate < purchaseDate) throw new Error(`Row ${rowNumber}: draw_date cannot be earlier than purchase_date.`);
      const drawId = column.draw_id === undefined ? "" : row[column.draw_id].trim();
      if (drawId && !/^\d{1,12}$/.test(drawId)) {
        throw new Error(`Row ${rowNumber}: draw_id must contain 1 to 12 digits.`);
      }
      const combinations = parseCombinations(row[column.combinations], game, rowNumber);
      const paid = parseAmount(row[column.paid], "paid", rowNumber);
      const prize = parseAmount(row[column.prize], "prize", rowNumber);
      const resultValue = row[column.result].trim().toLowerCase();
      const resultAliases = {
        "pending draw": "pending",
        "no prize": "no_prize",
        "prize won": "won",
      };
      const result = resultAliases[resultValue] || resultValue;
      if (!results.has(result)) {
        throw new Error(`Row ${rowNumber}: result must be pending, no_prize, or won.`);
      }
      if (prize > 0 && result !== "won") {
        throw new Error(`Row ${rowNumber}: set result to won when prize is greater than zero.`);
      }
      const note = column.note === undefined ? "" : row[column.note];
      if (note.length > 160) throw new Error(`Row ${rowNumber}: note must be 160 characters or fewer.`);

      imported.push({ game, purchaseDate, drawDate, drawId, combinations, paid, prize, result, note });
    }
    return imported;
  }

  function quote(value) {
    let text = String(value);
    if (/^[\u0000-\u0020]*[=+\-@]/.test(text)) text = `'${text}`;
    return `"${text.replace(/"/g, '""')}"`;
  }

  function stringifyTickets(tickets) {
    const rows = [headers];
    tickets.forEach((ticket) => {
      rows.push([
        ticket.game,
        ticket.purchaseDate,
        ticket.drawDate,
        ticket.drawId || "",
        ticket.combinations.map((combination) => combination.join(" ")).join("; "),
        ticket.paid,
        ticket.prize,
        ticket.result,
        ticket.note,
      ]);
    });
    return `${rows.map((row) => row.map(quote).join(",")).join("\r\n")}\r\n`;
  }

  const api = { parseRows, parseTickets, stringifyTickets };
  root.DrawlogCsv = api;
  if (typeof module !== "undefined" && module.exports) module.exports = api;
})(globalThis);
