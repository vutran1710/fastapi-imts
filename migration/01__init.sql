CREATE TYPE "AuthProviders" AS ENUM (
  'facebook',
  'google',
  'app'
);

CREATE TABLE "users" (
  "id" uuid PRIMARY KEY,
  "created_at" timestamp DEFAULT current_timestamp,
  "email" varchar UNIQUE NOT NULL,
  "password" varchar,
  "token" varchar,
  "expire_at" timestamp,
  "provider" "AuthProviders"
);

CREATE TABLE "profiles" (
  "user_id" uuid,
  "full_name" varchar,
  "client" varchar
);

CREATE TABLE "images" (
  "id" uuid PRIMARY KEY,
  "name" varchar NOT NULL,
  "storage_key" varchar UNIQUE NOT NULL,
  "created_at" timestamp DEFAULT current_timestamp,
  "uploaded_by" uuid NULL
);

CREATE TABLE "tags" (
  "id" SERIAL PRIMARY KEY,
  "name" varchar UNIQUE NOT NULL
);

CREATE TABLE "tagged" (
  "tag" int,
  "image" uuid,
  "created_at" timestamp,
  PRIMARY KEY ("tag", "image")
);

ALTER TABLE "images" ADD FOREIGN KEY ("uploaded_by") REFERENCES "users" ("id") ON DELETE SET NULL;

ALTER TABLE "profiles" ADD FOREIGN KEY ("user_id") REFERENCES "users" ("id");

ALTER TABLE "tagged" ADD FOREIGN KEY ("tag") REFERENCES "tags" ("id");

ALTER TABLE "tagged" ADD FOREIGN KEY ("image") REFERENCES "images" ("id") ON DELETE CASCADE;

ALTER TABLE "tagged" ADD FOREIGN KEY ("tag") REFERENCES "tags" ("id") ON DELETE CASCADE;

CREATE INDEX ON "tagged" ("image");
