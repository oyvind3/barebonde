/* Barebonde Database Schema - Phase 1 & 2 */

/* Users and Authentication */
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    id_porten_id VARCHAR(255) UNIQUE NOT NULL,
    first_name VARCHAR(255),
    last_name VARCHAR(255),
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE refresh_tokens (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token VARCHAR(500) UNIQUE NOT NULL,
    expires_at TIMESTAMP NOT NULL,
    revoked BOOLEAN DEFAULT false,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_refresh_tokens_user_id ON refresh_tokens(user_id);
CREATE INDEX idx_refresh_tokens_token ON refresh_tokens(token);

/* Farms (Gårder) - Core entity */
CREATE TABLE farms (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    org_number VARCHAR(9) UNIQUE NOT NULL,
    address VARCHAR(255),
    municipality VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_farms_org_number ON farms(org_number);

/* Farm-User relationships with roles */
CREATE TYPE user_role AS ENUM ('owner', 'manager', 'staff');

CREATE TABLE farm_users (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    farm_id INTEGER NOT NULL REFERENCES farms(id) ON DELETE CASCADE,
    role user_role DEFAULT 'staff',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, farm_id)
);

CREATE INDEX idx_farm_users_user_id ON farm_users(user_id);
CREATE INDEX idx_farm_users_farm_id ON farm_users(farm_id);

/* Properties (Eiendommer) */
CREATE TABLE properties (
    id SERIAL PRIMARY KEY,
    farm_id INTEGER NOT NULL REFERENCES farms(id) ON DELETE CASCADE,
    name VARCHAR(255),
    area_hectares INTEGER,
    gardskart_id VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_properties_farm_id ON properties(farm_id);

/* Accounting - Transactions (Phase 2) */
CREATE TYPE transaction_type AS ENUM ('income', 'expense');

CREATE TABLE transactions (
    id SERIAL PRIMARY KEY,
    farm_id INTEGER NOT NULL REFERENCES farms(id) ON DELETE CASCADE,
    type transaction_type NOT NULL,
    amount DECIMAL(10, 2) NOT NULL,
    description VARCHAR(500),
    category VARCHAR(100),
    date DATE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_transactions_farm_id ON transactions(farm_id);
CREATE INDEX idx_transactions_date ON transactions(date);
CREATE INDEX idx_transactions_category ON transactions(category);

/* Documents (Phase 2) */
CREATE TYPE document_type AS ENUM (
    'contract', 
    'invoice', 
    'insurance', 
    'permit', 
    'certificate', 
    'other'
);

CREATE TABLE documents (
    id SERIAL PRIMARY KEY,
    farm_id INTEGER NOT NULL REFERENCES farms(id) ON DELETE CASCADE,
    type document_type NOT NULL,
    title VARCHAR(255) NOT NULL,
    file_path VARCHAR(500),
    file_size INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_documents_farm_id ON documents(farm_id);
CREATE INDEX idx_documents_type ON documents(type);

/* Contracts/Agreements (Phase 2) */
CREATE TABLE contracts (
    id SERIAL PRIMARY KEY,
    farm_id INTEGER NOT NULL REFERENCES farms(id) ON DELETE CASCADE,
    title VARCHAR(255) NOT NULL,
    start_date DATE,
    end_date DATE,
    document_id INTEGER REFERENCES documents(id),
    is_signed BOOLEAN DEFAULT false,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_contracts_farm_id ON contracts(farm_id);
CREATE INDEX idx_contracts_end_date ON contracts(end_date);

/* Deadlines/Frister (Phase 2) */
CREATE TYPE deadline_type AS ENUM (
    'regulatory',      -- Tax, VAT, etc
    'agricultural',    -- Subsidies, farming dates
    'business',        -- Contract renewals
    'legal',           -- Permits, certificates
    'custom'           -- User-defined
);

CREATE TABLE deadlines (
    id SERIAL PRIMARY KEY,
    farm_id INTEGER NOT NULL REFERENCES farms(id) ON DELETE CASCADE,
    title VARCHAR(255) NOT NULL,
    type deadline_type NOT NULL,
    due_date DATE NOT NULL,
    description TEXT,
    is_completed BOOLEAN DEFAULT false,
    related_document_id INTEGER REFERENCES documents(id),
    related_contract_id INTEGER REFERENCES contracts(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_deadlines_farm_id ON deadlines(farm_id);
CREATE INDEX idx_deadlines_due_date ON deadlines(due_date);
CREATE INDEX idx_deadlines_type ON deadlines(type);

/* Audit trail for sensitive operations */
CREATE TABLE audit_logs (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id),
    farm_id INTEGER NOT NULL REFERENCES farms(id),
    action VARCHAR(100) NOT NULL,
    entity_type VARCHAR(100),
    entity_id INTEGER,
    changes JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_audit_logs_farm_id ON audit_logs(farm_id);
CREATE INDEX idx_audit_logs_created_at ON audit_logs(created_at);
