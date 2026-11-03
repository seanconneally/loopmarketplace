# ADR 0004 — Direct uploads and VideoProvider

Accepted locally; managed EU adapter proposed for production. Scoped multipart URLs keep video bytes off the API, while ffmpeg workers produce private derivatives and publish only after checks. SeaweedFS supplies local S3 storage. This boundary permits managed transcoding later without changing listing/chat logic; source/CDN cleanup still needs provider-specific operations.
