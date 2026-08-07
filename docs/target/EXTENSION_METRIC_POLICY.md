# Extension Metric Policy

> **Milestone 9**

1. Unknown / unresolved metrics become extension **candidates**, never approved metrics.
2. Suggested namespace is `cim:extension.<slug>` from the raw key.
3. Justification placeholder is required on create; review_status stays under_review / pending / candidate.
4. Duplicates return the existing candidate.
5. `approve()` marks accepted but keeps review_status under_review until catalogue promotion.
6. Extension candidates must not receive approved standards mappings automatically.
