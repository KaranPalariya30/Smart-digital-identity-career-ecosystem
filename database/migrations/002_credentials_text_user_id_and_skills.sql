-- Run after 001 on an existing PostgreSQL database.
-- (SQLite deployments do not need this: the service creates the table itself.)
--
-- 1. auth-service user ids are integers, so credentials.user_id can no longer
--    be a UUID. Store the id as text.
-- 2. Each credential can list the skills it verifies. The resume service
--    receives them as `verified_skills`.

ALTER TABLE credentials
    ALTER COLUMN user_id TYPE VARCHAR(64) USING user_id::text;

ALTER TABLE credentials
    ADD COLUMN IF NOT EXISTS skills VARCHAR(500);
