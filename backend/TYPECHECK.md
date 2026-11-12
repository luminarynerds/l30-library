# Backend type-check gate

The PR gate blocks a new `file::error-code` signature. It permits the existing
signatures in `.mypy-baseline.json`; passing this gate does not mean the backend
has no type errors. Multiple diagnostics in the same file with the same error
code share a signature, so this gate cannot detect another error of that pair.

Use Python 3.12 and the CI environment from the backend directory:

```sh
python -m venv .venv-typecheck
. .venv-typecheck/bin/activate
pip install -r requirements-typecheck.txt
python -m unittest discover -s scripts/tests -v
python scripts/mypy_delta.py
```

`requirements-typecheck.txt` pins the checker and its resolved dependency
environment. These pins apply to type checking only. They do not change the
production dependency metadata or establish dependency security clearance.
Checker launch, configuration and unrecognized diagnostic failures exit 2;
neither `--warn` nor `--rebaseline` may hide them.

## Baseline maintenance

Do not refresh the baseline merely to make a changed application pass. First
run the same pinned environment against both the untouched base revision and
the proposed application. Review every difference attributable to changed code.
Only independently reproduced existing debt belongs in a baseline refresh.
Keep new application diagnostics out of that refresh.

On 2026-10-25, the untouched base
`dddc2a4496492d9c80ddf8dc57886be528e9b525` and the release-readiness branch had
identical application files and mypy configuration. Separate checks against
both source trees, using Python 3.12.4, mypy 2.4.0, SQLAlchemy 2.1.6 and the pinned
environment, produced exactly the same 2,033 signatures (zero set differences).
Compared with the old 1,907-signature baseline, 302 signatures were newly
recognized and 176 were no longer reported. The baseline was refreshed from
the untouched base output. These are existing diagnostics under the current
environment, not application defects introduced or repaired by this PR.

Future tool/dependency updates must repeat this comparison deliberately. Preserve
the commands, versions, source revisions and signature-set comparison in the
review before running `python scripts/mypy_delta.py --rebaseline`.
