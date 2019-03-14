DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'item') THEN
        CREATE TYPE item AS (
            id INT,
            name VARCHAR(32),
            cost NUMERIC(7, 2)
        );
    END IF;
END $$;

CREATE TABLE IF NOT EXISTS players (
    owner_id BIGINT PRIMARY KEY UNIQUE NOT NULL,
    "name" VARCHAR(32) NOT NULL,
    map_id INT NOT NULL DEFAULT 0,
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT (NOW() AT TIME ZONE 'utc'),
    explored INT[] NOT NULL DEFAULT '{0}'::INT[],
    exp INT NOT NULL DEFAULT 0,
    inventory item[] NOT NULL DEFAULT '{}'::item[]
);

CREATE TABLE IF NOT EXISTS blacklist (
    user_id BIGINT PRIMARY KEY UNIQUE NOT NULL,
    reason VARCHAR(255) NOT NULL
);

CREATE TABLE IF NOT EXISTS shop (
    "item" item NOT NULL,
    level_requirement INT NOT NULL DEFAULT 0
);
