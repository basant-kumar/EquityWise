# Contributing to EquityWise

Thank you for improving EquityWise. Contributions through issues and pull
requests are open to everyone.

## Pull request permissions

EquityWise is a public repository, so any signed-in GitHub user can fork it and
open a pull request. A fork owner controls their fork and can update or close
their pull request.

Opening a pull request does not grant permission to merge into the upstream
EquityWise repository. Only maintainers and collaborators with suitable GitHub
access can merge an approved pull request.

## Before starting

- Search existing issues and pull requests for related work.
- Open an issue before a large change so the approach can be agreed first.
- Keep each pull request focused on one bug or feature.
- Never include real financial or personal data.

## Development setup

Fork the repository on GitHub, then clone your fork:

```bash
git clone https://github.com/YOUR-USERNAME/EquityWise.git
cd EquityWise
git remote add upstream https://github.com/basant-kumar/EquityWise.git
uv sync --extra dev
```

Create a branch from the latest upstream `main`:

```bash
git fetch upstream
git switch main
git merge --ff-only upstream/main
git switch -c fix/short-description
```

## Make and verify changes

- Follow the existing code and test structure.
- Add regression tests for bug fixes and tests for new behavior.
- Use synthetic, anonymized fixtures only.
- Update user-facing documentation when commands or behavior change.

Run the checks:

```bash
uv run pytest -q
uv run ruff check src tests
```

Before committing, inspect the exact files and content being added:

```bash
git status --short
git diff --check
git diff
```

## Financial-data privacy

Do not commit or attach any of the following:

- Files from `data/user_data/`
- Benefit History, G&L, RSU/ESPP, or bank statements
- Generated tax reports from `output/`
- Names, addresses, tax identifiers, account numbers, grant identifiers, or
  transaction details belonging to a real person
- Debug logs containing source-file contents or personal paths

When reproducing a bug, create the smallest synthetic fixture that demonstrates
it. If a pull request exposes sensitive data, remove it from the branch history
before requesting review; deleting it in a later commit is not sufficient.

## Open a pull request

Push the feature branch to your fork and open a pull request targeting
`basant-kumar/EquityWise:main`:

```bash
git push -u origin fix/short-description
```

The pull request should include:

- A concise problem and solution description
- Any behavior or report-format changes
- Tests run and their result
- Relevant issue links
- Confirmation that no private financial data is included

Maintainers may request changes. Continue pushing fixes to the same branch; the
pull request updates automatically. A maintainer will merge it after approval.

## Reporting bugs

Open a GitHub issue with the EquityWise version, command used, expected behavior,
actual behavior, and a minimal anonymized example. Never paste source statements
or generated reports containing private information.

## License

By contributing, you agree that your contribution will be licensed under the
repository's [MIT License](LICENSE).
