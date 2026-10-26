-- Least-privilege grants for the application role.
-- Create the role first (the password stays out of Git):
--   sudo -u postgres psql -c "CREATE ROLE shortly_app LOGIN PASSWORD 'choose-a-strong-one';"
-- Then, connected to the shortly database:
--   sudo -u postgres psql -d shortly -f db/grants.sql
--
-- The app can read, add and update links. It can't delete rows, change the
-- schema, create tables or touch any other database.

REVOKE ALL ON DATABASE shortly FROM PUBLIC;
GRANT CONNECT ON DATABASE shortly TO shortly_app;

REVOKE CREATE ON SCHEMA public FROM PUBLIC;
GRANT USAGE ON SCHEMA public TO shortly_app;

GRANT SELECT, INSERT, UPDATE ON links TO shortly_app;
GRANT USAGE ON SEQUENCE links_id_seq TO shortly_app;
