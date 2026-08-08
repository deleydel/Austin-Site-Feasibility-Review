# Manual verification

Open `manual_review_sheet.csv`, fill the `your_verdict` column for every row, save it as `manual_review_completed.csv` in this folder, then run:

```
python -m evaluation.manual.build_sheet --score
```

Allowed values by stratum:

- `retrieval_relevance`: relevant / not_relevant
- `structured_data`: correct / incorrect
- `citation_support`: supported / partially_supported / unsupported / uncited

The sheet does not show what the automated evaluation decided. That is deliberate: seeing the machine's answer next to your box would pull your answer toward it, and the agreement between the two is exactly what is being measured. The verdicts are held in `manual_review_key.json` and joined in when you run `--score`.
