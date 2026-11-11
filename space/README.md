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

The interface includes the latest published results from Vietlott for
information only. It never checks or changes personal tickets.

Ticket records and imported CSV files stay in the current browser tab. Drawlog
uses Gradio only to host its static interface; it does not send records to an
application backend or save them to browser storage. Refreshing or closing the
tab clears the records. This is a public Space; the hosting provider may
process ordinary network request metadata.

Import a CSV, edit or remove records, then export a new CSV file. The selected
input file is never modified.

See the [Drawlog repository](https://github.com/tpc-pascal/drawlog) for local
setup, CSV format, and project details.
