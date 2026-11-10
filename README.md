<p align="center">
  <img src="assets/logo.svg" alt="Drawlog — lottery ticket tracker" width="380"/>
</p>

<p align="center">
  <a href="https://github.com/tpc-pascal/drawlog/stargazers"><img src="https://img.shields.io/github/stars/tpc-pascal/drawlog?label=stars" alt="GitHub stars"></a>
  <a href="https://github.com/tpc-pascal/drawlog/actions/workflows/ci.yml"><img src="https://github.com/tpc-pascal/drawlog/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
  <a href="https://github.com/tpc-pascal/drawlog/issues"><img src="https://img.shields.io/github/issues/tpc-pascal/drawlog?label=issues" alt="Open issues"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-blue.svg" alt="MIT License"></a>
</p>

Drawlog is a personal Vietlott ticket ledger. Record number combinations,
purchase and draw dates, spending, and prizes in a compact browser interface.

## Run locally

```bash
git clone https://github.com/tpc-pascal/drawlog.git
cd drawlog
python3 -m http.server 8000
```

Open <http://localhost:8000> in a modern browser. No package installation or
build step is required.

Ticket records stay in the current tab's memory only. They are lost when the
page is refreshed or closed.

## Features

- Enter purchase and draw dates as three `DD / MM / YYYY` fields.
- Add number combinations for Mega 6/55, Mega 6/45, and Max 3D.
- Validate number counts, ranges, and duplicates for supported games.
- Record the amount paid, including a zero-cost FREE voucher, draw result,
  prize amount, and an optional note.
- Review ticket records and session totals for paid, prizes, and net amount.
- Import a CSV, edit or remove tickets, and export the current list to a new
  CSV file.
- Use the responsive form on desktop and mobile screens.

Draw-result lookup, automatic prize matching, and persistent storage are not
included. The interface does not send ticket data to a server.

## Data and privacy

Drawlog's source code is public. Ticket records currently remain in memory in
the browser and are not sent to or stored by a server.

Never commit ticket records, CSV files, credentials, or other personal data to
this public repository. If CSV storage is introduced, keep those files in a
separate private repository or private storage; GitHub Releases on this public
repository are public too.

## Project structure

| Path | Purpose |
|---|---|
| [`index.html`](index.html) | Ticket entry page and live summary |
| [`web/app.js`](web/app.js) | Form interactions and in-session ticket list |
| [`web/csv.js`](web/csv.js) | In-memory CSV parsing, validation, and export |
| [`web/games.js`](web/games.js) | Game definitions and number validation |
| [`web/styles.css`](web/styles.css) | Responsive interface styling |
| [`tests/`](tests/) | Game, CSV, privacy, and hosted-runtime tests |
| [`.github/workflows/ci.yml`](.github/workflows/ci.yml) | Automated tests and syntax checks |
| [`assets/logo.svg`](assets/logo.svg) | Drawlog wordmark |
| [`assets/social-preview.svg`](assets/social-preview.svg) | Editable social preview artwork |
| [`assets/social-preview.png`](assets/social-preview.png) | GitHub social preview image |

## Checks

Run the game validation tests with Node.js:

```bash
node --test
```

Check JavaScript syntax with:

```bash
node --check web/games.js
node --check web/app.js
```

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for the lightweight contribution
workflow. Do not include personal ticket CSV files, credentials, or other
private records in commits or issue reports.

## Security

For security concerns, see [SECURITY.md](SECURITY.md). Do not report ticket
data or credentials in a security report.

## License

[MIT](LICENSE) © tpc-pascal.

Drawlog is a personal project and is not affiliated with or endorsed by
Vietlott.
