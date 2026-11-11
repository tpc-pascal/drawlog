---
title: Drawlog
emoji: 🎟️
colorFrom: green
colorTo: yellow
sdk: gradio
sdk_version: 6.31.0
app_file: app.py
pinned: false
license: mit
short_description: Private-by-design Vietlott ticket ledger
---

# Drawlog

A browser-based personal Vietlott ticket ledger.

The ledger supports Mega 6/55, Mega 6/45, Power 6/55, Lotto 5/35, Bingo18,
Max 3D, Max 3D Pro, and Keno.

The interface includes the latest published results from Vietlott and can
automatically check pending tickets against historical draws.

Ticket records and imported CSV files stay in the current browser tab. Drawlog
sends only a product code and draw date to its Gradio host for historical
lookups. Ticket numbers and combinations are matched in the browser and are
never sent to the host or Vietlott. Drawlog does not save ticket data to browser
storage; refreshing or closing the tab clears the records. This is a public
Space; the hosting provider may process ordinary network request metadata.

Vietlott is the primary history source. If Vietlott denies a lookup, Mega 6/45
and Power 6/55 can use a clearly labeled xoso.net.vn fallback. Verify secondary
results with Vietlott before acting on them.

Import a CSV, edit or remove records, then export a new CSV file. The selected
input file is never modified.

See the [Drawlog repository](https://github.com/tpc-pascal/drawlog) for local
setup, CSV format, and project details.
