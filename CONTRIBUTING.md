# Contributing

This private repository supports reproducible research on carbon-aware EV charging. Contributions should preserve scientific traceability and computational reproducibility.

## Contribution principles

1. Keep assumptions and scenario parameters in `config/config.yaml` whenever practical.
2. Preserve deterministic random seeds unless a change explicitly studies stochastic variation.
3. Never edit generated result files without regenerating them from code.
4. Add or update tests when changing model logic, calculations, or output schemas.
5. Record user-visible changes in `CHANGELOG.md`.

## Local validation

Before proposing a change, run:

```bash
python -m pytest -q
python -m src.validation.final_quality_control
```

For changes that affect simulation results, rerun the appropriate workflow described in `docs/REPRODUCIBILITY.md` and inspect the updated figures and tables.

## Change workflow

- Create a focused branch from `main`.
- Use clear commit messages that describe the scientific or documentation change.
- Explain any changed assumptions, metrics, or numerical results in the pull request.
- Do not commit credentials, local environments, application caches, or document-render previews.

## Data and generated outputs

Public source archives are retained for provenance. Processed, synthetic, and result files are versioned to make the released analysis inspectable. If an output becomes too large for the repository, document how to regenerate it and store it using an approved archival mechanism.
