CREATE TABLE IF NOT EXISTS api_tokens (
    id SERIAL PRIMARY KEY,
    provider VARCHAR(50) NOT NULL,
    access_token TEXT NOT NULL,
    refresh_token TEXT,
    token_type VARCHAR(20) DEFAULT 'Bearer',
    expires_at TIMESTAMP WITH TIME ZONE,
    realm_id VARCHAR(50),
    extra_data JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS customers (
    id SERIAL PRIMARY KEY,
    qb_id VARCHAR(50) UNIQUE NOT NULL,
    display_name VARCHAR(255),
    email VARCHAR(255),
    balance NUMERIC(12, 2),
    is_active BOOLEAN DEFAULT TRUE,
    raw_data JSONB,
    synced_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS products_services (
    id SERIAL PRIMARY KEY,
    qb_id VARCHAR(50) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    type VARCHAR(50),
    unit_price NUMERIC(12, 2),
    cost NUMERIC(12, 2),
    description TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    raw_data JSONB,
    synced_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS revenue (
    id SERIAL PRIMARY KEY,
    qb_id VARCHAR(50) UNIQUE NOT NULL,
    qb_type VARCHAR(50),
    customer_id INTEGER REFERENCES customers(id),
    product_service_id INTEGER REFERENCES products_services(id),
    txn_date DATE NOT NULL,
    amount NUMERIC(12, 2) NOT NULL,
    quantity NUMERIC(10, 2) DEFAULT 1,
    description TEXT,
    raw_data JSONB,
    synced_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS expenses (
    id SERIAL PRIMARY KEY,
    qb_id VARCHAR(50) UNIQUE NOT NULL,
    qb_type VARCHAR(50),
    vendor_name VARCHAR(255),
    account_name VARCHAR(255),
    product_service_id INTEGER REFERENCES products_services(id),
    txn_date DATE NOT NULL,
    amount NUMERIC(12, 2) NOT NULL,
    description TEXT,
    raw_data JSONB,
    synced_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS liabilities (
    id SERIAL PRIMARY KEY,
    qb_account_id VARCHAR(50) NOT NULL,
    account_name VARCHAR(255),
    account_type VARCHAR(50),
    balance NUMERIC(12, 2),
    balance_date DATE,
    raw_data JSONB,
    synced_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(qb_account_id, balance_date)
);

CREATE TABLE IF NOT EXISTS analysis_snapshots (
    id SERIAL PRIMARY KEY,
    snapshot_date DATE UNIQUE NOT NULL,
    total_revenue NUMERIC(12, 2),
    total_expenses NUMERIC(12, 2),
    net_profit NUMERIC(12, 2),
    total_liabilities NUMERIC(12, 2),
    product_breakdown JSONB,
    insights JSONB,
    forecast JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS operational_data (
    id SERIAL PRIMARY KEY,
    source VARCHAR(50) NOT NULL,
    data_type VARCHAR(100),
    reference_date DATE,
    amount NUMERIC(12, 2),
    quantity NUMERIC(10, 2),
    metadata JSONB,
    synced_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS chat_history (
    id SERIAL PRIMARY KEY,
    session_id UUID NOT NULL,
    role VARCHAR(20) NOT NULL,
    content TEXT NOT NULL,
    function_call JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_revenue_txn_date ON revenue(txn_date);
CREATE INDEX IF NOT EXISTS idx_revenue_product ON revenue(product_service_id);
CREATE INDEX IF NOT EXISTS idx_expenses_txn_date ON expenses(txn_date);
CREATE INDEX IF NOT EXISTS idx_expenses_product ON expenses(product_service_id);
CREATE INDEX IF NOT EXISTS idx_liabilities_date ON liabilities(balance_date);
CREATE INDEX IF NOT EXISTS idx_operational_source ON operational_data(source);
CREATE INDEX IF NOT EXISTS idx_chat_session ON chat_history(session_id);
