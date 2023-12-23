BEGIN TRANSACTION;
DROP TABLE IF EXISTS "Prices";
CREATE TABLE IF NOT EXISTS "Prices" (
	"timestamp"	TEXT,
	"item_id"	TEXT,
	"price"	NUMERIC
);
DROP TABLE IF EXISTS "Users";
CREATE TABLE IF NOT EXISTS "Users" (
	"id"	TEXT NOT NULL UNIQUE,
	"name"	TEXT,
	PRIMARY KEY("id")
);
DROP TABLE IF EXISTS "Items";
CREATE TABLE IF NOT EXISTS "Items" (
	"id"	TEXT NOT NULL UNIQUE,
	PRIMARY KEY("id")
);
DROP TABLE IF EXISTS "UserItems";
CREATE TABLE IF NOT EXISTS "UserItems" (
	"user_id"	TEXT NOT NULL,
	"item_id"	TEXT NOT NULL,
	"item_name"	TEXT,
	"added"	TEXT NOT NULL,
	FOREIGN KEY("item_id") REFERENCES "Items"("id"),
	FOREIGN KEY("user_id") REFERENCES "Users"("id")
);
DROP TABLE IF EXISTS "UserAgents";
CREATE TABLE IF NOT EXISTS "UserAgents" (
	"id"	INTEGER,
	"ua"	TEXT NOT NULL,
	"added"	TEXT,
	"count"	INTEGER DEFAULT 0,
	PRIMARY KEY("id" AUTOINCREMENT)
);
COMMIT;
