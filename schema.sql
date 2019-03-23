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
    explored INT[] NOT NULL DEFAULT ARRAY[]::INT[],
    exp INT NOT NULL DEFAULT 0,
    compendium_data INT[188]
);

CREATE TABLE IF NOT EXISTS blacklist (
    user_id BIGINT PRIMARY KEY UNIQUE NOT NULL,
    reason VARCHAR(255) NOT NULL
);

CREATE TABLE IF NOT EXISTS encounters (
    name VARCHAR(32) NOT NULL,
    id INT PRIMARY KEY UNIQUE NOT NULL,
    map_ids INT[] NOT NULL DEFAULT array[149947],
    tier_requirement INT NOT NULL DEFAULT 1
);
-- 1 is the bare minimum you must be in order to win.
-- if you are lower than this, it is impossible for you to win.
-- as your level increases, your likeliness to win also does
-- eg if you are level 1, you have a 16% chance to win
-- level 2: 33%, level 3: 50% and so on
-- exp is determined on the tier requirement.
-- eg req 1 will give you like 7 exp or smth idk

CREATE TABLE IF NOT EXISTS shop (
    "item" item NOT NULL,
    level_requirement INT NOT NULL DEFAULT 0
);
