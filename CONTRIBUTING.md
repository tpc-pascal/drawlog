# Contributing to Drawlog

Thanks for your interest in Drawlog. The project is currently a small,
personal-use application; focused fixes and improvements are welcome.

## Development setup

```bash
git clone https://github.com/tpc-pascal/drawlog.git
cd drawlog
python3 -m http.server 8000
```

Open <http://localhost:8000> to try the interface. Node.js is required to run
the game validation tests:

```bash
node --test
```

## Workflow

1. Create a focused branch, such as `feat/short-description` or
   `fix/short-description`.
2. Keep changes small and update tests when behavior changes.
3. Run the tests and JavaScript syntax checks before submitting changes.
4. Describe the motivation and user-visible effect in the pull request.

## Data and commits

Never commit ticket or draw CSV files, credentials, or private ticket records.
This repository is public, and its GitHub Releases and attached assets are
public as well. Keep personal data in a separate private repository or private
storage.
