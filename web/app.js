(function () {
  "use strict";

  const { games, validateCombinations } = window.DrawlogGames;
  const { parseTickets, stringifyTickets } = window.DrawlogCsv;
  const { fetchDrawHistory, checkTicket: compareTicket } = window.DrawlogTicketCheck;
  const form = document.getElementById("ticket-form");
  const gameSelect = document.getElementById("game");
  const numberSets = document.getElementById("number-sets");
  const numberHint = document.getElementById("number-hint");
  const paidInput = document.getElementById("paid");
  const freeInput = document.getElementById("free");
  const errorBox = document.getElementById("form-error");
  const csvFile = document.getElementById("csv-file");
  const csvStatus = document.getElementById("csv-status");
  const csvError = document.getElementById("csv-error");
  const exportButton = document.getElementById("export-csv");
  const tickets = [];
  const currency = new Intl.NumberFormat("en-US", { maximumFractionDigits: 0 });
  const latestResults = window.DrawlogResults.products;
  const latestResultsList = document.getElementById("latest-results-list");
  const resultsUpdated = document.getElementById("results-updated");
  const tabList = document.querySelector('[role="tablist"]');
  const tabs = Array.from(tabList.querySelectorAll('[role="tab"]'));

  Object.entries(games).forEach(([id, game]) => {
    const option = document.createElement("option");
    option.value = id;
    option.textContent = game.label;
    gameSelect.append(option);
  });

  function renderCombination() {
    const game = games[gameSelect.value];
    numberHint.textContent = game.hint;
    numberSets.replaceChildren();
    addCombination();
  }

  function addCombination() {
    const game = games[gameSelect.value];
    const row = document.createElement("div");
    row.className = `number-row${game.kind === "three_digit" ? " number-row-three" : ""}`;
    if (game.kind === "three_digit_pair") row.classList.add("number-row-pair");
    if (game.kind === "keno") row.classList.add("number-row-keno");
    if (game.kind === "lotto_special") row.classList.add("number-row-special");
    if (game.kind === "bingo18") row.classList.add("number-row-bingo18");
    row.setAttribute("role", "group");
    row.setAttribute("aria-label", `Combination ${numberSets.children.length + 1}`);

    if (game.kind === "bingo18") {
      const select = document.createElement("select");
      select.setAttribute("aria-label", "Bingo18 outcome");
      game.choices.forEach((choice) => {
        const option = document.createElement("option");
        option.value = choice.value;
        option.textContent = choice.label;
        select.append(option);
      });
      row.append(select);
    } else if (game.kind === "three_digit" || game.kind === "three_digit_pair") {
      for (let index = 0; index < game.count; index += 1) {
        row.append(makeNumberInput(
          game.count === 1 ? "Three-digit number" : `Three-digit number ${index + 1}`,
          "000",
          3,
          true,
        ));
      }
    } else if (game.kind === "lotto_special") {
      for (let index = 0; index < game.mainCount; index += 1) {
        row.append(makeNumberInput(`Main number ${index + 1}`, String(index + 1).padStart(2, "0"), 2, true));
      }
      const special = makeNumberInput("Special number", "SP", 2, true);
      special.classList.add("special-number");
      row.append(special);
    } else if (game.kind === "keno") {
      for (let index = 0; index < game.count; index += 1) {
        row.append(makeNumberInput(`Keno number ${index + 1}`, String(index + 1).padStart(2, "0"), 2, false));
      }
    } else {
      for (let index = 0; index < game.count; index += 1) {
        row.append(makeNumberInput(`Number ${index + 1}`, String(index + 1).padStart(2, "0"), 2, true));
      }
    }

    const remove = document.createElement("button");
    remove.type = "button";
    remove.className = "remove-set";
    remove.setAttribute("aria-label", `Remove combination ${numberSets.children.length + 1}`);
    remove.textContent = "×";
    remove.disabled = numberSets.children.length === 0;
    remove.addEventListener("click", () => {
      row.remove();
      updateCombinationRows();
    });
    row.append(remove);
    numberSets.append(row);
  }

  function makeNumberInput(label, placeholder, maxLength, required) {
    const input = document.createElement("input");
    input.type = "text";
    input.inputMode = "numeric";
    input.autocomplete = "off";
    input.maxLength = maxLength;
    input.placeholder = placeholder;
    input.setAttribute("aria-label", label);
    input.required = required;
    input.addEventListener("input", () => {
      input.value = input.value.replace(/\D/g, "").slice(0, maxLength);
    });
    return input;
  }

  function updateCombinationRows() {
    Array.from(numberSets.children).forEach((row, index) => {
      row.setAttribute("aria-label", `Combination ${index + 1}`);
      const remove = row.querySelector(".remove-set");
      remove.setAttribute("aria-label", `Remove combination ${index + 1}`);
      remove.disabled = numberSets.children.length === 1;
    });
  }

  document.querySelectorAll(".date-inputs").forEach((group) => {
    const inputs = Array.from(group.querySelectorAll("input"));
    inputs.forEach((input, index) => {
      input.addEventListener("input", () => {
        input.value = input.value.replace(/\D/g, "").slice(0, input.maxLength);
        if (input.value.length === input.maxLength && index < inputs.length - 1) {
          inputs[index + 1].focus();
        }
      });
      input.addEventListener("keydown", (event) => {
        if (event.key === "Backspace" && input.value === "" && index > 0) {
          inputs[index - 1].focus();
        }
      });
    });
  });

  function readDate(name) {
    const group = document.querySelector(`[data-date="${name}"]`);
    const [dayText, monthText, yearText] = Array.from(group.querySelectorAll("input"), (input) => input.value);
    if (!/^\d{2}$/.test(dayText) || !/^\d{2}$/.test(monthText) || !/^\d{4}$/.test(yearText)) {
      return null;
    }
    const day = Number(dayText);
    const month = Number(monthText);
    const year = Number(yearText);
    const date = new Date(Date.UTC(year, month - 1, day));
    if (date.getUTCFullYear() !== year || date.getUTCMonth() !== month - 1 || date.getUTCDate() !== day) {
      return null;
    }
    return `${yearText}-${monthText}-${dayText}`;
  }

  function readCombinations() {
    return Array.from(numberSets.children, (row) =>
      Array.from(row.querySelectorAll("input, select"), (input) => input.value.trim())
        .filter((value) => value !== ""),
    );
  }

  function formatCombination(gameId, combination) {
    const game = games[gameId];
    if (game.kind === "bingo18") {
      return [...game.choices, ...game.legacyChoices]
        .find((choice) => choice.value === combination[0])?.label || combination[0];
    }
    if (game.kind === "lotto_special") {
      return `${combination.slice(0, game.mainCount).join(" · ")} · SP ${combination[game.mainCount]}`;
    }
    return combination.join(" · ");
  }

  function showError(message) {
    errorBox.textContent = message;
    errorBox.hidden = false;
  }

  function formatDate(isoDate) {
    const [year, month, day] = isoDate.split("-");
    return `${day}/${month}/${year}`;
  }

  function formatMoney(amount) {
    return `${currency.format(amount)} ₫`;
  }

  function activateTab(tab, moveFocus = false) {
    tabs.forEach((currentTab) => {
      const selected = currentTab === tab;
      currentTab.setAttribute("aria-selected", String(selected));
      currentTab.tabIndex = selected ? 0 : -1;
      document.getElementById(currentTab.getAttribute("aria-controls")).hidden = !selected;
    });
    if (moveFocus) tab.focus();
  }

  tabList.addEventListener("click", (event) => {
    const tab = event.target.closest('[role="tab"]');
    if (tab && tabList.contains(tab)) activateTab(tab);
  });

  tabList.addEventListener("keydown", (event) => {
    const currentIndex = tabs.indexOf(event.target);
    if (currentIndex === -1) return;

    let nextIndex;
    if (event.key === "ArrowRight") nextIndex = (currentIndex + 1) % tabs.length;
    else if (event.key === "ArrowLeft") nextIndex = (currentIndex - 1 + tabs.length) % tabs.length;
    else if (event.key === "Home") nextIndex = 0;
    else if (event.key === "End") nextIndex = tabs.length - 1;
    else return;

    event.preventDefault();
    activateTab(tabs[nextIndex], true);
  });

  function makeResultNumbers(numbers) {
    const list = document.createElement("div");
    list.className = "latest-result-numbers";
    numbers.forEach((number) => {
      const chip = document.createElement("span");
      chip.className = "number-chip";
      chip.textContent = number;
      list.append(chip);
    });
    return list;
  }

  function renderLatestResults() {
    latestResultsList.replaceChildren();
    const updatedAt = window.DrawlogResults.updated_at;
    if (updatedAt && Number.isFinite(Date.parse(updatedAt))) {
      const updatedDate = new Date(updatedAt);
      resultsUpdated.textContent = `Snapshot updated ${new Intl.DateTimeFormat("en", {
        dateStyle: "medium",
        timeStyle: "short",
        timeZone: "UTC",
      }).format(updatedDate)} UTC`;
    } else {
      resultsUpdated.textContent = "Showing the last verified snapshot";
    }

    latestResults.forEach((result) => {
      const card = document.createElement("article");
      card.className = "latest-result-card";

      const heading = document.createElement("div");
      heading.className = "latest-result-heading";
      const game = document.createElement("h3");
      game.textContent = result.label;
      const source = document.createElement("a");
      source.href = result.source_url;
      source.target = "_blank";
      source.rel = "noopener noreferrer";
      source.textContent = result.source_label || "Vietlott";
      source.setAttribute("aria-label", `${result.label} results from ${source.textContent}`);
      heading.append(game, source);

      const draw = document.createElement("p");
      draw.className = "latest-result-draw";
      draw.textContent = `#${result.draw_id} · ${formatDate(result.draw_date)}${result.stale ? " · Last verified result" : ""}`;
      card.append(heading, draw);

      if (result.prize_groups) {
        result.prize_groups.forEach((group) => {
          const groupCard = document.createElement("section");
          groupCard.className = "latest-prize-group";
          const groupTitle = document.createElement("h4");
          groupTitle.textContent = group.mode;
          groupCard.append(groupTitle);
          group.prizes.forEach((prize) => {
            const prizeRow = document.createElement("div");
            prizeRow.className = "latest-prize-row";
            const prizeName = document.createElement("span");
            prizeName.textContent = prize.prize;
            prizeRow.append(prizeName, makeResultNumbers(prize.numbers));
            groupCard.append(prizeRow);
          });
          card.append(groupCard);
        });
      } else {
        card.append(makeResultNumbers(result.numbers));
        if (result.special) {
          const special = document.createElement("p");
          special.className = "latest-result-detail";
          special.textContent = `Special: ${result.special}`;
          card.append(special);
        }
        const details = [];
        if (result.total !== undefined) details.push(`Total ${result.total}`);
        if (result.size) details.push(result.size);
        if (result.parity) details.push(result.parity);
        if (details.length) {
          const detail = document.createElement("p");
          detail.className = "latest-result-detail";
          detail.textContent = details.join(" · ");
          card.append(detail);
        }
      }
      latestResultsList.append(card);
    });
  }

  function isValidIsoDate(value) {
    if (!/^\d{4}-\d{2}-\d{2}$/.test(value)) return false;
    const [year, month, day] = value.split("-").map(Number);
    const date = new Date(Date.UTC(year, month - 1, day));
    return date.getUTCFullYear() === year && date.getUTCMonth() === month - 1 && date.getUTCDate() === day;
  }

  function makeTicketEditor(ticket) {
    const details = document.createElement("details");
    details.className = "ticket-editor";
    details.innerHTML = `
      <summary>Edit ticket</summary>
      <form class="ticket-edit-form">
        <label>Game type
          <select name="game">${Object.entries(games).map(([id, game]) =>
            `<option value="${id}">${escapeHtml(game.label)}</option>`,
          ).join("")}</select>
        </label>
        <div class="edit-date-grid">
          <label>Purchase date<input name="purchaseDate" type="date" required></label>
          <label>Draw date<input name="drawDate" type="date" required></label>
        </div>
        <label>Draw number <small>Optional; needed to distinguish games with multiple draws per day.</small>
          <input name="drawId" type="text" inputmode="numeric" maxlength="12">
        </label>
        <label>Combinations <small>Separate numbers with spaces and combinations with semicolons.</small>
          <textarea name="combinations" rows="3" required></textarea>
        </label>
        <div class="edit-date-grid">
          <label>Amount paid (VND)<input name="paid" type="number" min="0" step="1" required></label>
          <label>Prize amount (VND)<input name="prize" type="number" min="0" step="1" required></label>
        </div>
        <label>Draw result
          <select name="result">
            <option value="pending">Pending draw</option>
            <option value="no_prize">No prize</option>
            <option value="won">Prize won</option>
          </select>
        </label>
        <label>Note<input name="note" type="text" maxlength="160"></label>
        <p class="form-error edit-error" role="alert" hidden></p>
        <div class="edit-actions">
          <button class="button button-primary" type="submit">Save changes</button>
          <button class="button button-quiet cancel-edit" type="button">Cancel</button>
        </div>
      </form>`;

    const editor = details.querySelector("form");
    editor.elements.namedItem("game").value = ticket.game;
    editor.elements.namedItem("purchaseDate").value = ticket.purchaseDate;
    editor.elements.namedItem("drawDate").value = ticket.drawDate;
    editor.elements.namedItem("drawId").value = ticket.drawId || "";
    editor.elements.namedItem("combinations").value = ticket.combinations
      .map((combination) => combination.join(" "))
      .join("; ");
    editor.elements.namedItem("paid").value = String(ticket.paid);
    editor.elements.namedItem("prize").value = String(ticket.prize);
    editor.elements.namedItem("result").value = ticket.result;
    editor.elements.namedItem("note").value = ticket.note;
    editor.querySelector(".cancel-edit").addEventListener("click", renderTickets);
    editor.addEventListener("submit", (event) => {
      event.preventDefault();
      const error = editor.querySelector(".edit-error");
      error.hidden = true;
      const game = editor.elements.namedItem("game").value;
      const purchaseDate = editor.elements.namedItem("purchaseDate").value;
      const drawDate = editor.elements.namedItem("drawDate").value;
      const drawId = editor.elements.namedItem("drawId").value.trim();
      if (!isValidIsoDate(purchaseDate) || !isValidIsoDate(drawDate)) {
        error.textContent = "Enter valid purchase and draw dates.";
        error.hidden = false;
        return;
      }
      if (drawDate < purchaseDate) {
        error.textContent = "Draw date cannot be earlier than the purchase date.";
        error.hidden = false;
        return;
      }

      const combinations = editor.elements.namedItem("combinations").value
        .trim()
        .split(";")
        .map((combination) => combination.trim().split(/[\s,|]+/).filter(Boolean));
      const combinationErrors = validateCombinations(game, combinations);
      if (combinationErrors.length) {
        error.textContent = combinationErrors[0];
        error.hidden = false;
        return;
      }

      const paid = Number(editor.elements.namedItem("paid").value);
      const prize = Number(editor.elements.namedItem("prize").value);
      if (!Number.isSafeInteger(paid) || paid < 0 || !Number.isSafeInteger(prize) || prize < 0) {
        error.textContent = "Paid and prize amounts must be valid non-negative VND amounts.";
        error.hidden = false;
        return;
      }
      const result = editor.elements.namedItem("result").value;
      if (prize > 0 && result !== "won") {
        error.textContent = "Select “Prize won” when entering a prize amount.";
        error.hidden = false;
        return;
      }
      const note = editor.elements.namedItem("note").value;
      if (note.length > 160) {
        error.textContent = "Note must be 160 characters or fewer.";
        error.hidden = false;
        return;
      }

      if (drawId && !/^\d{1,12}$/.test(drawId)) {
        error.textContent = "Draw number must contain 1 to 12 digits.";
        error.hidden = false;
        return;
      }

      const drawChanged = game !== ticket.game ||
        drawDate !== ticket.drawDate ||
        drawId !== (ticket.drawId || "") ||
        JSON.stringify(combinations) !== JSON.stringify(ticket.combinations);
      Object.assign(ticket, { game, purchaseDate, drawDate, drawId, combinations, paid, prize, result, note });
      if (drawChanged) {
        ticket.result = "pending";
        ticket.prize = 0;
        ticket.autoChecked = false;
        ticket.checkState = "";
        ticket.checkMessage = "";
        ticket.drawResults = null;
      }
      renderTickets();
      if (drawChanged) void checkTicketResult(ticket);
    });
    return details;
  }

  function escapeHtml(value) {
    return String(value).replace(/[&<>"']/g, (character) => ({
      "&": "&amp;",
      "<": "&lt;",
      ">": "&gt;",
      '"': "&quot;",
      "'": "&#39;",
    })[character]);
  }

  function renderTickets() {
    const list = document.getElementById("ticket-list");
    const emptyState = document.getElementById("empty-state");
    list.replaceChildren();
    emptyState.hidden = tickets.length > 0;

    let paidTotal = 0;
    let prizeTotal = 0;
    tickets.forEach((ticket) => {
      paidTotal += ticket.paid;
      prizeTotal += ticket.prize;
      const card = document.createElement("article");
      card.className = "ticket-card";
      const combinations = ticket.combinations.map((combination) =>
        `<span class="number-chip">${escapeHtml(formatCombination(ticket.game, combination))}</span>`,
      ).join("");
      const resultLabel = {
        pending: "Pending draw",
        no_prize: "No prize",
        won: "Prize won",
      }[ticket.result];
      card.innerHTML = `
        <div class="ticket-card-top">
          <div><span class="game-tag">${escapeHtml(games[ticket.game].label)}</span>
            <span class="ticket-date">Draw ${formatDate(ticket.drawDate)}</span></div>
          <button type="button" class="delete-ticket" aria-label="Remove ticket">×</button>
        </div>
        <div class="ticket-combinations">${combinations}</div>
        <div class="ticket-card-bottom">
          <span>${escapeHtml(resultLabel)}${ticket.note ? ` · ${escapeHtml(ticket.note)}` : ""}</span>
          <strong>${formatMoney(ticket.prize)} <small>prize</small></strong>
        </div>
        <div class="ticket-paid">Paid ${formatMoney(ticket.paid)} · Purchased ${formatDate(ticket.purchaseDate)}</div>`;
      if (ticket.checkMessage || ticket.checkState === "choose_draw" || ticket.result === "pending") {
        const checkPanel = document.createElement("div");
        checkPanel.className = "ticket-check-panel";
        if (ticket.checkMessage) {
          const message = document.createElement("p");
          message.className = `ticket-check-message${ticket.checkState === "error" ? " is-error" : ""}`;
          message.textContent = ticket.checkMessage;
          checkPanel.append(message);
        }
        if (ticket.checkState === "choose_draw" && ticket.drawResults?.length) {
          const label = document.createElement("label");
          label.className = "ticket-draw-picker";
          label.textContent = "Draw number on ticket";
          const select = document.createElement("select");
          select.setAttribute("aria-label", "Select the draw number printed on your ticket");
          const placeholder = document.createElement("option");
          placeholder.value = "";
          placeholder.textContent = "Select a draw";
          select.append(placeholder);
          ticket.drawResults.forEach((draw) => {
            const option = document.createElement("option");
            option.value = draw.draw_id;
            option.textContent = `#${draw.draw_id}`;
            select.append(option);
          });
          select.value = ticket.drawId || "";
          select.addEventListener("change", () => {
            const selectedDraw = ticket.drawResults.find((draw) => draw.draw_id === select.value);
            if (selectedDraw) applyDrawCheck(ticket, selectedDraw);
          });
          label.append(select);
          checkPanel.append(label);
        }
        if (ticket.result === "pending") {
          const checkButton = document.createElement("button");
          checkButton.type = "button";
          checkButton.className = "button button-quiet ticket-check-button";
          checkButton.textContent = ticket.checkState === "checking" ? "Checking…" : "Check result";
          checkButton.disabled = ticket.checkState === "checking";
          checkButton.addEventListener("click", () => { void checkTicketResult(ticket); });
          checkPanel.append(checkButton);
        }
        card.append(checkPanel);
      } else if (ticket.autoChecked) {
        const checkedDraw = ticket.drawResults?.find((draw) => draw.draw_id === ticket.drawId);
        const sourceLabel = checkedDraw?.source_label || "Vietlott";
        const verified = document.createElement("p");
        verified.className = "ticket-check-verified";
        if (sourceLabel === "Vietlott") {
          verified.textContent = `Checked against official draw #${ticket.drawId}. Verify the prize amount before recording it.`;
        } else {
          verified.textContent =
            `Checked against secondary source ${sourceLabel} draw #${ticket.drawId}. Verify on Vietlott before recording a prize. `;
          if (checkedDraw?.source_url) {
            const sourceLink = document.createElement("a");
            sourceLink.href = checkedDraw.source_url;
            sourceLink.target = "_blank";
            sourceLink.rel = "noopener noreferrer";
            sourceLink.textContent = "View source.";
            verified.append(sourceLink);
          }
        }
        card.append(verified);
      }
      card.querySelector(".delete-ticket").addEventListener("click", () => {
        tickets.splice(tickets.indexOf(ticket), 1);
        renderTickets();
      });
      card.append(makeTicketEditor(ticket));
      list.append(card);
    });

    document.getElementById("ticket-count").textContent = String(tickets.length);
    document.getElementById("record-count").textContent =
      `${tickets.length} ${tickets.length === 1 ? "record" : "records"}`;
    document.getElementById("total-paid").textContent = formatMoney(paidTotal);
    document.getElementById("total-prizes").textContent = formatMoney(prizeTotal);
    document.getElementById("net-total").textContent = formatMoney(prizeTotal - paidTotal);
    exportButton.disabled = tickets.length === 0;
  }

  function applyDrawCheck(ticket, draw) {
    ticket.drawId = draw.draw_id;
    const outcome = compareTicket(ticket.game, ticket.combinations, draw);
    if (outcome === null) {
      ticket.checkState = "unverified";
      ticket.checkMessage = "This ticket type cannot be verified confidently from the published result. The record remains pending.";
      ticket.autoChecked = false;
    } else {
      ticket.result = outcome;
      ticket.checkState = "checked";
      ticket.checkMessage = "";
      ticket.autoChecked = true;
    }
    renderTickets();
  }

  async function checkTicketResult(ticket) {
    if (ticket.checkState === "checking") return;
    ticket.checkState = "checking";
    ticket.checkMessage = "Looking up published draw data. Ticket numbers stay in this browser.";
    renderTickets();
    try {
      const draws = await fetchDrawHistory(ticket.game, ticket.drawDate);
      if (draws.length === 0) {
        ticket.checkState = "unavailable";
        ticket.checkMessage = "No official draw is available for this product and date yet.";
        return;
      }
      ticket.drawResults = draws;
      const selectedDraw = ticket.drawId
        ? draws.find((draw) => draw.draw_id === ticket.drawId)
        : draws.length === 1 ? draws[0] : null;
      if (!selectedDraw) {
        ticket.checkState = "choose_draw";
        ticket.checkMessage = draws.length === 1
          ? `Draw #${ticket.drawId} was not found for this date. Select the draw number printed on your ticket.`
          : `${draws.length} draws were published that day. Select the draw number printed on your ticket.`;
        return;
      }
      applyDrawCheck(ticket, selectedDraw);
    } catch (error) {
      ticket.checkState = "error";
      ticket.checkMessage = `Could not verify this ticket: ${error.message}`;
    } finally {
      if (ticket.checkState !== "checking") renderTickets();
    }
  }

  function checkPendingTickets(importedTickets) {
    importedTickets
      .filter((ticket) => ticket.result === "pending")
      .forEach((ticket) => { void checkTicketResult(ticket); });
  }

  function showCsvMessage(message, isError) {
    csvStatus.hidden = isError || !message;
    csvError.hidden = !isError || !message;
    if (isError) csvError.textContent = message;
    else csvStatus.textContent = message;
  }

  gameSelect.addEventListener("change", renderCombination);
  document.getElementById("add-set").addEventListener("click", () => {
    addCombination();
    updateCombinationRows();
    numberSets.lastElementChild.querySelector("input, select").focus();
  });
  freeInput.addEventListener("change", () => {
    paidInput.value = freeInput.checked ? "0" : "10000";
    paidInput.readOnly = freeInput.checked;
  });

  csvFile.addEventListener("change", async () => {
    const file = csvFile.files[0];
    csvFile.value = "";
    if (!file) return;
    showCsvMessage("", false);
    try {
      const imported = parseTickets(await file.text());
      if (
        tickets.length > 0 &&
        !window.confirm(`Import ${imported.length} tickets and replace the ${tickets.length} current in-memory records?`)
      ) {
        showCsvMessage("Import cancelled. Your current in-memory records are unchanged.", false);
        return;
      }
      tickets.length = 0;
      imported.forEach((ticket) => tickets.push(ticket));
      renderTickets();
      checkPendingTickets(imported);
      showCsvMessage(
        `Imported ${imported.length} ${imported.length === 1 ? "ticket" : "tickets"}. Data remains in this tab's memory only.`,
        false,
      );
    } catch (error) {
      showCsvMessage(`Could not import CSV: ${error.message}`, true);
    }
  });

  exportButton.addEventListener("click", () => {
    if (tickets.length === 0) return;
    const blob = new Blob([stringifyTickets(tickets)], { type: "text/csv;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    const now = new Date();
    const localDate = [
      now.getFullYear(),
      String(now.getMonth() + 1).padStart(2, "0"),
      String(now.getDate()).padStart(2, "0"),
    ].join("-");
    link.download = `drawlog-${localDate}.csv`;
    link.click();
    window.setTimeout(() => URL.revokeObjectURL(url), 1000);
    showCsvMessage("Downloaded a new CSV. Your input file was not changed.", false);
  });

  form.addEventListener("submit", (event) => {
    event.preventDefault();
    errorBox.hidden = true;
    const purchaseDate = readDate("purchase");
    const drawDate = readDate("draw");
    if (!purchaseDate || !drawDate) {
      showError("Enter valid purchase and draw dates in DD / MM / YYYY format.");
      return;
    }
    if (drawDate < purchaseDate) {
      showError("Draw date cannot be earlier than the purchase date.");
      return;
    }

    const combinations = readCombinations();
    const combinationErrors = validateCombinations(gameSelect.value, combinations);
    if (combinationErrors.length) {
      showError(combinationErrors[0]);
      return;
    }

    const paid = Number(paidInput.value);
    const prize = Number(document.getElementById("prize").value);
    if (!Number.isSafeInteger(paid) || paid < 0 || !Number.isSafeInteger(prize) || prize < 0) {
      showError("Paid and prize amounts must be valid non-negative VND amounts.");
      return;
    }
    if (freeInput.checked && paid !== 0) {
      showError("A FREE voucher must have an amount paid of zero.");
      return;
    }
    const result = document.getElementById("result").value;
    if (prize > 0 && result !== "won") {
      showError("Select “Prize won” when entering a prize amount.");
      return;
    }

    const ticket = {
      game: gameSelect.value,
      purchaseDate,
      drawDate,
      drawId: document.getElementById("draw-id").value.trim(),
      combinations,
      paid,
      prize,
      result,
      note: document.getElementById("note").value.trim(),
    };
    if (ticket.drawId && !/^\d{1,12}$/.test(ticket.drawId)) {
      showError("Draw number must contain 1 to 12 digits.");
      return;
    }
    tickets.unshift(ticket);
    renderTickets();
    if (ticket.result === "pending") void checkTicketResult(ticket);
    form.reset();
    paidInput.value = "10000";
    paidInput.readOnly = false;
    document.getElementById("prize").value = "0";
    document.getElementById("result").value = "pending";
    document.querySelectorAll(".date-inputs input").forEach((input) => { input.value = ""; });
    renderCombination();
    document.querySelector('[data-date="purchase"] input').focus();
  });

  renderCombination();
  renderLatestResults();
  renderTickets();
})();
