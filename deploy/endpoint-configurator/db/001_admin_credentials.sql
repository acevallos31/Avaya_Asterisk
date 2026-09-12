-- Endpoint Configurator administrative credential foundation.
-- Apply only in LAB during Test 67. Values are always ciphertext; plaintext is never stored.
CREATE TABLE IF NOT EXISTS pbx_admin_password_policy (
    id TINYINT UNSIGNED NOT NULL,
    pbx_identity VARCHAR(191) NOT NULL,
    active_version INT UNSIGNED NOT NULL DEFAULT 0,
    pending_version INT UNSIGNED NULL,
    ciphertext MEDIUMTEXT NULL,
    key_reference VARCHAR(191) NOT NULL,
    status VARCHAR(32) NOT NULL DEFAULT 'UNCONFIGURED',
    created_at DATETIME NOT NULL,
    rotated_at DATETIME NULL,
    PRIMARY KEY (id),
    UNIQUE KEY uq_pbx_admin_password_policy_identity (pbx_identity)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS endpoint_admin_credential (
    id_endpoint INT UNSIGNED NOT NULL,
    source VARCHAR(16) NOT NULL,
    ciphertext MEDIUMTEXT NULL,
    key_reference VARCHAR(191) NOT NULL,
    version INT UNSIGNED NOT NULL DEFAULT 0,
    validation_status VARCHAR(32) NOT NULL DEFAULT 'PENDING',
    last_validated_at DATETIME NULL,
    rotation_status VARCHAR(32) NOT NULL DEFAULT 'NONE',
    updated_at DATETIME NOT NULL,
    PRIMARY KEY (id_endpoint),
    CONSTRAINT fk_endpoint_admin_credential_endpoint
        FOREIGN KEY (id_endpoint) REFERENCES endpoint(id) ON DELETE CASCADE,
    CONSTRAINT chk_endpoint_admin_credential_source
        CHECK (source IN ('GLOBAL', 'OVERRIDE', 'FACTORY'))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS endpoint_credential_event (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    id_endpoint INT UNSIGNED NULL,
    operation VARCHAR(32) NOT NULL,
    result VARCHAR(32) NOT NULL,
    actor VARCHAR(191) NOT NULL,
    correlation_id CHAR(36) NOT NULL,
    created_at DATETIME NOT NULL,
    PRIMARY KEY (id),
    KEY idx_endpoint_credential_event_endpoint (id_endpoint),
    KEY idx_endpoint_credential_event_created (created_at),
    CONSTRAINT fk_endpoint_credential_event_endpoint
        FOREIGN KEY (id_endpoint) REFERENCES endpoint(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
