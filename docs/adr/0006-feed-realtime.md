# ADR 0006 — Stable feed and durable realtime

Accepted. Five-minute bounded ranked snapshots avoid changing-score pagination duplicates; expired state asks the client to restart and recency keysets provide degradation. Persist chat before pub/sub and recover from REST history because pub/sub has no replay. The cost is explicit snapshot expiry/projection maintenance and reconnect handling.
