BEGIN TRANSACTION;
CREATE TABLE IF NOT EXISTS "Prices" (
	"timestamp"	TEXT,
	"item_id"	TEXT,
	"price"	NUMERIC
);
CREATE TABLE IF NOT EXISTS "Users" (
	"id"	TEXT NOT NULL UNIQUE,
	"name"	TEXT,
	"refresh_time"		INTEGER DEFAULT 86400,
	"min_variation"		NUMERIC DEFAULT 0.03,
	"deal_variation"	NUMERIC DEFAULT 0.15,
	PRIMARY KEY("id")
);
CREATE TABLE IF NOT EXISTS "Items" (
	"id" TEXT NOT NULL UNIQUE,
	PRIMARY KEY("id")
);
CREATE TABLE IF NOT EXISTS "UserItems" (
	"user_id"	TEXT NOT NULL,
	"item_id"	TEXT NOT NULL,
	"item_name"	TEXT,
	"added"		TEXT NOT NULL,
	FOREIGN KEY("item_id") REFERENCES "Items"("id"),
	FOREIGN KEY("user_id") REFERENCES "Users"("id")
);
CREATE TABLE IF NOT EXISTS "UserAgents" (
	"id"	INTEGER,
	"ua"	TEXT NOT NULL,
	"added"	TEXT,
	"count"	INTEGER DEFAULT 0,
	PRIMARY KEY("id" AUTOINCREMENT)
);
COMMIT;