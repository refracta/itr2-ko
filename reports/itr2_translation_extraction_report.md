# Into the Radius 2 Korean Translation Extraction Report

## Source Extraction

- Base `Game.locres`: 2164 entries, 1282 strings, 1282 unique strings, 28867 unique chars.
- Base `Game.locres` namespaces: default 1231 entries, EnglishSource 933 entries.
- Base `EnglishSource.uasset`: 3301 GUID/text pairs, 2461 unique strings, 130287 unique chars.
- Combined translation records: 5465 location records = 2164 locres + 3301 uasset.
- Deduped source queue: 3535 unique sources, 3427 translatable, 156479 translatable chars.

## Mod Coverage

### Russian

- `Game.locres`: exact key coverage of base locres: 2164 / 2164 entries.
- Russian locres still same as English for 214 entries, mostly numbers/tokens/placeholders.
- `EnglishSource.uasset`: current base has 3301 unique keys; Russian uasset has 2447 unique keys.
- Russian uasset covers 2444 current base uasset keys and misses 857 keys.
- Keys with any Cyrillic translation in common: 2391.

### Japanese fUyU 1.0.5

- Japanese locres contains 4701 entries.
- It covers all 2164 base locres keys and adds 2537 extra EnglishSource keys.
- Japanese EnglishSource keys: 3470.
- This equals the union of base locres EnglishSource and base uasset keys, but key collisions exist.

## Key Collision Finding

- `EnglishSource` key alone is not a safe identity.
- 600 locres EnglishSource records share a key with uasset records but have different English text.
- Therefore Korean patch generation should patch `Game.locres` and `EnglishSource.uasset` separately, not merge everything into one locres by key.

## Translation Run

- Codex translation chunks: 19.
- Completed translated rows: 3427 / 3427.
- Missing: 0; duplicates: 0; placeholder issues: 0.
- Heuristic Latin residue rows: 11 (saved as `latin_residue_sample.json`).

## Output Paths

- Records with Korean: `work/translation_targets/records_with_ko.json`
- Unique source map with Korean: `work/translation_targets/unique_sources_with_ko.json`
- Per-chunk translations: `work/translation_targets/translations/`
- Validation summary: `work/translation_targets/post_translation_validation.json`
- This report: `work/reports/itr2_translation_extraction_report.md`
