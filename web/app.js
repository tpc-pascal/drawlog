(function () {
  "use strict";

  const { games, validateCombinations } = window.DrawlogGames;
  const form = document.getElementById("ticket-form");
  const gameSelect = document.getElementById("game");
  const numberSets = document.getElementById("number-sets");
  const numberHint = document.getElementById("number-hint");
  const paidInput = document.getElementById("paid");
  const freeInput = document.getElementById("free");
  const errorBox = document.getElementById("form-error");
  const tickets = [];
  const currency = new Intl.NumberFormat("en-US", { maximumFractionDigits: 0 });

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
    row.className = `number-row ${game.kind === "three_digit" ? "number-row-three" : ""}`;
    row.setAttribute("role", "group");
    row.setAttribute("aria-label", `Combination ${numberSets.children.length + 1}`);

    if (game.kind === "three_digit") {
      row.append(makeNumberInput("Three-digit number", "000", 3));
    } else {
      for (let index = 0; index < game.count; index += 1) {
        row.append(makeNumberInput(`Number ${index + 1}`, String(index + 1).padStart(2, "0"), 2));
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

  function makeNumberInput(label, placeholder, maxLength) {
    const input = document.createElement("input");
    input.type = "text";
    input.inputMode = "numeric";
    input.autocomplete = "off";
    input.maxLength = maxLength;
    input.placeholder = placeholder;
    input.setAttribute("aria-label", label);
    input.required = true;
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
      Array.from(row.querySelectorAll("input"), (input) => input.value.trim()),
    );
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
        `<span class="number-chip">${combination.map(escapeHtml).join(" · ")}</span>`,
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
      card.querySelector(".delete-ticket").addEventListener("click", () => {
        tickets.splice(tickets.indexOf(ticket), 1);
        renderTickets();
      });
      list.append(card);
    });

    document.getElementById("ticket-count").textContent = String(tickets.length);
    document.getElementById("record-count").textContent =
      `${tickets.length} ${tickets.length === 1 ? "record" : "records"}`;
    document.getElementById("total-paid").textContent = formatMoney(paidTotal);
    document.getElementById("total-prizes").textContent = formatMoney(prizeTotal);
    document.getElementById("net-total").textContent = formatMoney(prizeTotal - paidTotal);
  }

  gameSelect.addEventListener("change", renderCombination);
  document.getElementById("add-set").addEventListener("click", () => {
    addCombination();
    updateCombinationRows();
    numberSets.lastElementChild.querySelector("input").focus();
  });
  freeInput.addEventListener("change", () => {
    paidInput.value = freeInput.checked ? "0" : "10000";
    paidInput.readOnly = freeInput.checked;
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

    tickets.unshift({
      game: gameSelect.value,
      purchaseDate,
      drawDate,
      combinations,
      paid,
      prize,
      result,
      note: document.getElementById("note").value.trim(),
    });
    renderTickets();
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
  renderTickets();
})();
