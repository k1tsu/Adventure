CREATE TABLE IF NOT EXISTS players (
    owner_id BIGINT PRIMARY KEY UNIQUE NOT NULL,
    "name" VARCHAR(32) NOT NULL,
    map_id INT NOT NULL DEFAULT 0,
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT (NOW() AT TIME ZONE 'utc'),
    explored INT[] NOT NULL DEFAULT '{0}'::INT[],
    coins DECIMAL(2) NOT NULL DEFAULT 0.00,
    exp INT NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS blacklist (
    user_id BIGINT PRIMARY KEY UNIQUE NOT NULL,
    reason VARCHAR(255) NOT NULL
);

CREATE TABLE IF NOT EXISTS shop (
    name VARCHAR(32) NOT NULL,
    cost NUMERIC(10, 2) NOT NULL,
    level_requirement INT NOT NULL DEFAULT 0,
    item_id SERIAL PRIMARY KEY
);

INSERT INTO shop (name, cost, level_requirement, item_id) VALUES ('null', 0, 0, 0) ON CONFLICT(item_id) DO NOTHING;