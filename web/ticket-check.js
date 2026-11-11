(function (root) {
  "use strict";

  const kenoWinningMatches = {
    1: [1],
    2: [2],
    3: [2, 3],
    4: [2, 3, 4],
    5: [2, 3, 4, 5],
    6: [2, 3, 4, 5, 6],
    7: [0, 3, 4, 5, 6, 7],
    8: [0, 3, 4, 5, 6, 7, 8],
    9: [0, 4, 5, 6, 7, 8, 9],
    10: [0, 4, 5, 6, 7, 8, 9, 10],
  };
  const knownMax3dProPrizes = new Set(["Special", "First", "Second", "Third", "Fourth", "Fifth", "Sixth"]);
  const historyCache = new Map();

  function parseEventStream(text) {
    let payload = null;
    let eventType = "";
    for (const line of text.split(/\r?\n/)) {
      if (line.startsWith("event: ")) {
        eventType = line.slice(7);
        continue;
      }
      if (!line.startsWith("data: ")) continue;
      try {
        payload = JSON.parse(line.slice(6));
      } catch (error) {
        throw new Error("Drawlog received an invalid result response.");
      }
    }
    if (eventType === "error") {
      const error = payload && typeof payload.error === "string" ? payload.error : "";
      throw new Error(error || "The result service returned an error without details.");
    }
    const data = Array.isArray(payload) ? payload : payload?.data;
    if (!payload || payload.error || !Array.isArray(data)) {
      throw new Error(payload?.error || "Drawlog received an invalid result response.");
    }
    const [result] = data;
    const envelope = Array.isArray(result) && result.length === 1 &&
      result[0] && typeof result[0] === "object" && !Array.isArray(result[0]) &&
      Object.hasOwn(result[0], "draws")
      ? result[0]
      : result && !Array.isArray(result) && typeof result === "object" &&
        Object.hasOwn(result, "draws")
        ? result
        : null;
    if (envelope?.error) throw new Error(envelope.error);
    const draws = envelope ? envelope.draws : result;
    if (!Array.isArray(draws)) throw new Error("Drawlog received an unexpected draw-history response.");
    return draws;
  }

  async function fetchDrawHistory(gameId, drawDate, fetchImpl = root.fetch.bind(root)) {
    const cacheKey = `${gameId}\u0000${drawDate}`;
    if (historyCache.has(cacheKey)) return historyCache.get(cacheKey);

    const requestPromise = (async () => {
      const request = await fetchImpl("/gradio_api/call/lookup_official_draws", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ data: [gameId, drawDate] }),
      });
      if (!request.ok) throw new Error(`Draw history request failed (HTTP ${request.status}).`);
      const queued = await request.json();
      if (!queued.event_id) throw new Error("Drawlog could not start the official result lookup.");

      const response = await fetchImpl(
        `/gradio_api/call/lookup_official_draws/${encodeURIComponent(queued.event_id)}`,
        { headers: { Accept: "text/event-stream" } },
      );
      if (!response.ok) throw new Error(`Draw history request failed (HTTP ${response.status}).`);
      return parseEventStream(await response.text());
    })();
    historyCache.set(cacheKey, requestPromise);

    try {
      const draws = await requestPromise;
      if (draws.length === 0) historyCache.delete(cacheKey);
      return draws;
    } catch (error) {
      historyCache.delete(cacheKey);
      throw error;
    }
  }

  function checkCombination(gameId, combination, draw) {
    const values = combination.map(String);
    if (gameId === "mega_6_45" || gameId === "power_6_55") {
      const mainMatches = values.filter((number) => draw.numbers.includes(number)).length;
      if (gameId === "mega_6_45") return mainMatches >= 3;
      const specialMatches = values.filter((number) => number === draw.special).length;
      return mainMatches >= 3 || (mainMatches === 5 && specialMatches === 1);
    }

    if (gameId === "lotto_5_35") {
      const mainMatches = values.slice(0, 5).filter((number) => draw.numbers.includes(number)).length;
      const specialMatch = values[5] === draw.special;
      if (mainMatches >= 3) return true;
      if (mainMatches === 2 && specialMatch) return null;
      return false;
    }

    if (gameId === "bingo_18") {
      const outcome = values[0];
      if (outcome === "odd") return null;
      const numbers = draw.numbers.map(Number);
      const total = numbers.reduce((sum, number) => sum + number, 0);
      const sizeOutcome = outcome === "even" ? "tie" : outcome;
      if (sizeOutcome === "big") return total >= 12;
      if (sizeOutcome === "small") return total <= 9;
      if (sizeOutcome === "tie") return total === 10 || total === 11;
      if (outcome === "any_triple") return new Set(numbers).size === 1;
      const sumMatch = /^sum_(\d+)$/.exec(outcome);
      if (sumMatch) return total === Number(sumMatch[1]);
      const numberMatch = /^number_(\d+)$/.exec(outcome);
      if (numberMatch) return numbers.includes(Number(numberMatch[1]));
      const repeatedMatch = /^(pair|triple)_(\d+)$/.exec(outcome);
      if (repeatedMatch) {
        const occurrences = numbers.filter((number) => number === Number(repeatedMatch[2])).length;
        return repeatedMatch[1] === "pair" ? occurrences >= 2 : occurrences === 3;
      }
      return null;
    }

    if (gameId === "max_3d") {
      if (!draw.prize_groups?.length) return null;
      return draw.prize_groups.some((group) =>
        group.prizes.some((prize) => prize.numbers.includes(values[0])),
      );
    }

    if (gameId === "max_3d_pro") {
      if (values.length !== 2 || values[0] === values[1] || !draw.prize_groups?.length) return null;
      const prizes = draw.prize_groups.flatMap((group) => group.prizes);
      if (prizes.some((prize) => !knownMax3dProPrizes.has(prize.prize) || !prize.numbers.length)) {
        return null;
      }
      return prizes.some((prize) => {
        const matches = values.filter((number) => prize.numbers.includes(number)).length;
        if (prize.prize === "Special") {
          return matches === 2 && prize.numbers.length === 2;
        }
        if (["First", "Second", "Third", "Fourth"].includes(prize.prize)) return matches === 2;
        return matches >= 1;
      });
    }

    if (gameId === "keno") {
      const drawn = new Set(draw.numbers);
      const matched = values.filter((number) => drawn.has(number)).length;
      return kenoWinningMatches[values.length]?.includes(matched) ?? null;
    }

    return null;
  }

  function checkTicket(gameId, combinations, draw) {
    const outcomes = combinations.map((combination) => checkCombination(gameId, combination, draw));
    if (outcomes.includes(true)) return "won";
    if (outcomes.includes(null)) return null;
    return "no_prize";
  }

  const api = { fetchDrawHistory, checkCombination, checkTicket, parseEventStream };
  root.DrawlogTicketCheck = api;
  if (typeof module !== "undefined" && module.exports) module.exports = api;
})(globalThis);
