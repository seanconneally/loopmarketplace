# ADR 0005 — Rotating sessions

Accepted. Short access JWTs live in memory; opaque refresh tokens rotate in HttpOnly cookies with hashes persisted. Reuse revokes a family, cookie mutations validate Origin, and live account/session checks enforce suspension/logout. Extra database reads buy authoritative authorization instead of relying on stale role claims.
