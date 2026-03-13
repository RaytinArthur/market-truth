# Week1 vs Week2 Comparison
Case: AAPL @ 2024-08-05

## 1. Retrieval Difference
- Week1: vector-only news retrieval
- Week2: hybrid retrieval (vector + graph)

## 2. Evidence Difference
- Week1 only contains direct Apple-related news:
  - Berkshire sell-off
  - iPhone 16 order revision
  - analyst downgrade on services growth
- Week2 additionally includes related company / supply-chain evidence:
  - TSM/TSMC smartphone chip demand weakness
  - supply-chain-side corroboration for weak iPhone demand narrative

## 3. Analysis Difference
- Week1 explanation is mainly based on direct news aggregation.
- Week2 explanation is more complete because it includes indirect evidence from related companies.
- Week2 better supports the "demand weakness / supply-chain caution" narrative.

## 4. Current Issues
- Graph evidence is still limited (only 2 related items shown in final context).
- No explicit conflicting signals section yet.
- Confidence is still somewhat high relative to evidence strength.
- The report still tends to merge multiple factors into one broad narrative.

## 5. Interim Conclusion
- Week2 is more informative than Week1.
- Hybrid retrieval adds useful supply-chain corroboration.
- Next step: add ablation modes to test whether the model can still produce reasonable hypotheses without direct news.