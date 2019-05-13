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
    compendium_data SMALLINT[237],
    gold INT NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS blacklist (
    user_id BIGINT PRIMARY KEY UNIQUE NOT NULL,
    reason VARCHAR(255) NOT NULL
);

CREATE TABLE IF NOT EXISTS encounters (
    name VARCHAR(32) NOT NULL,
    map_ids INT[] NOT NULL DEFAULT array[149947],
    tier_requirement INT NOT NULL DEFAULT 1,
    id SERIAL PRIMARY KEY
);

CREATE TABLE IF NOT EXISTS shop (
    "item" item NOT NULL,
    level_requirement INT NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS supporters (
    userid BIGINT PRIMARY KEY UNIQUE NOT NULL,
    cstmbg TEXT DEFAULT NULL,
    textcol INT DEFAULT 16777215
);

CREATE TABLE IF NOT EXISTS tips (
    tip TEXT NOT NULL,
    id SERIAL PRIMARY KEY
);

CREATE TABLE IF NOT EXISTS bosses (
    name VARCHAR(32) NOT NULL,
    tier SMALLINT NOT NULL,
    id SERIAL PRIMARY KEY UNIQUE NOT NULL
);

CREATE TABLE IF NOT EXISTS persona_lookup (
    stats SMALLINT[] NOT NULL,
    name VARCHAR(32) PRIMARY KEY UNIQUE NOT NULL,
    hp INT NOT NULL,
    moves JSON NOT NULL -- {"movename": ["damage type", "severity"], ...}
);