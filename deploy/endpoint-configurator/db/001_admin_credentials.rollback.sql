-- Rollback for 001_admin_credentials.sql. Apply only after stopping credential rotation.
DROP TABLE IF EXISTS endpoint_credential_event;
DROP TABLE IF EXISTS endpoint_admin_credential;
DROP TABLE IF EXISTS pbx_admin_password_policy;
