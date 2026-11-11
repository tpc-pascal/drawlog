<p align="center">
  <img src="assets/logo.svg" alt="Drawlog" width="560"/>
</p>

<p align="center">
  <a href="https://github.com/tpc-pascal/drawlog/stargazers"><img src="https://img.shields.io/github/stars/tpc-pascal/drawlog?label=Stars" alt="Stars"></a>
  <a href="https://github.com/tpc-pascal/drawlog/actions/workflows/ci.yml"><img src="https://github.com/tpc-pascal/drawlog/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
  <a href="https://tpc-pascal-drawlog.hf.space"><img src="https://img.shields.io/badge/%F0%9F%A4%97%20Space-Drawlog-yellow" alt="Hugging Face Space"></a>
  <a href="https://github.com/tpc-pascal/drawlog/issues"><img src="https://img.shields.io/github/issues/tpc-pascal/drawlog?label=Issues" alt="Issues"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-blue.svg" alt="MIT License"></a>
</p>

Drawlog is a personal Vietlott ticket ledger. Track combinations, purchase and
draw dates, spending, vouchers, and prizes in a responsive browser interface.
Use it locally or open the [hosted Drawlog Space](https://tpc-pascal-drawlog.hf.space).

Ticket records stay in the current tab's memory. Drawlog does not upload them or
save them to browser storage; refreshing or closing the tab clears the records.
The Space uses Gradio to serve the interface, while ticket records and imported
CSV files are still processed only in your browser and are never sent to it.

## Features

- Record Power 6/55, Mega 6/45, Lotto 5/35, Bingo18, Max 3D, Max 3D Pro, and
  Keno tickets with product-specific validation.
- View the latest official draw results for every supported product; the public
  snapshot is refreshed hourly.
- Track purchase and draw dates, amount paid, FREE vouchers, results, prizes,
  and notes.
- Import a CSV, edit or remove records, and export the complete list to a new
  CSV file.
- Review ticket count, paid and prize totals, and net amount.
- Keep all records in browser memory without an account or ticket-data backend.

## Run locally

```bash
git clone https://github.com/tpc-pascal/drawlog.git
cd drawlog
python3 -m http.server 8000
```

Open <http://localhost:8000>. No package installation or build step is required.

## Hosted Space

Open [Drawlog on Hugging Face](https://tpc-pascal-drawlog.hf.space)
to use the same app without installing anything. The Space is public. It serves
the app files only; ticket records and CSV contents remain in your browser tab
and are not uploaded or saved by Drawlog. As with other hosted services, the
hosting provider may process ordinary network request metadata.

## Latest draw results

Drawlog includes a public snapshot of the latest results published on the
[official Vietlott website](https://vietlott.vn/). A GitHub Actions workflow
checks the homepage hourly, validates results for all seven products, and
updates the hosted Space when any result changes. The app displays these results
for reference only; it does not compare them with or change personal tickets.
The snapshot is bundled with the app, so viewing it makes no background network
request and does not send ticket data.

## CSV

Import requires the columns `game`, `purchase_date`, `draw_date`,
`combinations`, `paid`, `prize`, and `result`; `note` is optional. Dates accept
`YYYY-MM-DD` or `DD/MM/YYYY`. Separate combinations with semicolons and numbers
within a combination with spaces. Supported `game` values are `power_6_55`,
`mega_6_45`, `lotto_5_35`, `bingo_18`, `max_3d`, `max_3d_pro`, and `keno`.
Power 6/55 and Mega 6/45 require six distinct numbers in their respective
ranges. Lotto 5/35 uses five main numbers followed by its special number.
Bingo18 accepts `big`, `small`, `even`, `odd`, `sum_3` through `sum_18`,
`pair_1` through `pair_6`, or `triple_1` through `triple_6`. Max 3D takes one
three-digit number; Max 3D Pro takes two. Keno takes one to ten distinct numbers
from 1 to 80. The historical `mega_6_55` game ID and `Mega 6/55` label are
accepted on import and normalized to Power 6/55. `result` values are `pending`,
`no_prize`, and `won`.

The whole file is validated before import. Importing over existing records
requires confirmation. Export downloads a new file and never changes the
selected input file.

## Project structure

| Path | Purpose |
|---|---|
| [`index.html`](index.html) | Ticket entry page and live summary |
| [`web/app.js`](web/app.js) | Ticket entry, editing, and session-only records |
| [`web/games.js`](web/games.js) | Supported games and combination validation |
| [`web/csv.js`](web/csv.js) | In-memory CSV parsing, validation, and export |
| [`web/latest-results.js`](web/latest-results.js) | Public latest-draw snapshot bundled with the app |
| [`web/styles.css`](web/styles.css) | Responsive interface |
| [`tests/`](tests/) | Game validation, CSV, and privacy tests |
| [`scripts/update_latest_draws.py`](scripts/update_latest_draws.py) | Official result parsing and snapshot generation |
| [`app.py`](app.py) and [`requirements.txt`](requirements.txt) | Gradio host for the browser-only interface |
| [`.github/workflows/`](.github/workflows/) | CI, release, and Space maintenance workflows |
| [`scripts/check`](scripts/check) and [`scripts/release.sh`](scripts/release.sh) | Local validation and version tagging |
| [`assets/`](assets/) | Logo and social preview artwork |

## Checks

```bash
./scripts/check
```

Prepare a release by moving the relevant changelog entries into a dated
`## [vX.Y.Z]` section, then run `./scripts/release.sh vX.Y.Z`.

## Contributing

See [`CONTRIBUTING.md`](CONTRIBUTING.md) for the development workflow. Keep
ticket records, CSV files, credentials, and other personal data out of this
public repository, its release assets, and its Git history.

## Security

Report vulnerabilities privately as described in [`SECURITY.md`](SECURITY.md).
Do not include ticket records, CSV files, or credentials in a report.

## License

MIT — see [`LICENSE`](LICENSE). Drawlog is an independent personal project and
is not affiliated with or endorsed by Vietlott.
