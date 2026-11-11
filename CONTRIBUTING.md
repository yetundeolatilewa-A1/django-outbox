# Contributing

Bug reports and pull requests are welcome.

1. Fork and clone, then `pip install -e ".[dev]"`.
2. Make your change with a test. Run `python -m pytest`.
3. If you change models, run
   `PYTHONPATH=. DJANGO_SETTINGS_MODULE=tests.settings python -m django makemigrations django_outbox`
   and commit the migration.
4. Open a pull request describing the problem and the fix.

Please don't include real credentials or personal data in issues, tests or examples.
