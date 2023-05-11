DROP TABLE IF EXISTS verification_codes;

CREATE TABLE IF NOT EXISTS verification_codes(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    verification_code text NOT NULL,
    account_to_verify text UNIQUE,
    expiration_date INTEGER NOT NULL
);
