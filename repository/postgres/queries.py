"""Posgres SQL Plain Queries
Written to work with asyncpg
"""

FIND_USER_BY_EMAIL = "SELECT * FROM users WHERE email = $1"

FIND_USER_BY_ID = "SELECT * FROM users WHERE id = $1"

REGISTER_NEW_USER_APP = """
INSERT INTO users (email, password, provider)
VALUES ($1, $2, 'app')
ON CONFLICT DO NOTHING
RETURNING *
"""

REGISTER_NEW_USER_SOCIAL = """
INSERT INTO users (email, token, expire_at, provider)
VALUES ($1, $2, $3, $4)
RETURNING *
"""

UPDATE_USER_TOKEN = """
UPDATE users
SET token = $1, expire_at = $2, provider = $3
WHERE email = $4 RETURNING *
"""

GET_USER_TOKEN = """
SELECT token
FROM users
WHERE email = $1 AND expire_at > current_timestamp
"""

INSERT_NEW_IMAGE = """
INSERT INTO images (id, name, storage_key, uploaded_by)
VALUES ($1, $2, $3, $4)
RETURNING *
"""

FIND_IMAGE_BY_ID = """
WITH img AS (
    SELECT * FROM images WHERE id = $1
),
tag_ids AS (
    SELECT *
    FROM tagged
    WHERE image = $1
),
tag_names AS (
    SELECT string_agg(name, ',') AS tags
    FROM tags
    WHERE id IN (SELECT tag FROM tag_ids)
)
SELECT *
FROM img
LEFT JOIN tag_names ON TRUE;
"""

UPSERT_TAGS = """
WITH items (name) AS (SELECT r.name FROM unnest($1::tags[]) as r),
     added        AS
(
    INSERT INTO tags (name)
    SELECT name FROM items
    EXCEPT
    SELECT name FROM tags
    RETURNING id, name
)

SELECT id, name FROM added
UNION ALL
SELECT id, name FROM tags
WHERE name IN (SELECT name FROM items)
"""

INSERT_TAGGED_IMAGE = """
INSERT INTO tagged (tag, image, created_at)
(SELECT r.tag, r.image, r.created_at FROM unnest($1::tagged[]) as r)
RETURNING *
"""

GET_IMAGE_TAGS = """
WITH items (tag) AS (SELECT tag FROM tagged WHERE image = $1)
SELECT name
FROM tags
RIGHT JOIN items
ON tags.id = items.tag
"""

SEARCH_TAGGED_IMAGES = """
WITH tag_items AS (
        SELECT id, name
        FROM tags
        WHERE name IN (SELECT r.name FROM unnest($1::tags[]) as r)
),
image_ids AS (
        SELECT image
        FROM tagged
        WHERE tag in (SELECT id FROM tag_items)
        AND created_at >= $3 AND created_at <= $4
        GROUP BY image, created_at
        ORDER BY created_at DESC
        LIMIT $2
),
image_tag_ids AS (
        SELECT image, tag
        FROM tagged
        WHERE image in (SELECT image FROM image_ids)
),
image_tags AS (
        SELECT image, string_agg(tags.name, ',') as tags
        FROM image_tag_ids
        LEFT JOIN tags
        ON image_tag_ids.tag = tags.id
        GROUP BY image
),
image_tags_full_info AS (

SELECT images.*, image_tags.tags
        FROM image_tags
        LEFT JOIN images
        ON image_tags.image = images.id
        ORDER BY images.created_at DESC
)
SELECT * FROM image_tags_full_info
"""

SEARCH_TAGGED_IMAGES_WITH_PAGE = """
WITH tag_items AS (
        SELECT id, name
        FROM tags
        WHERE name IN (SELECT r.name FROM unnest($1::tags[]) as r)
),
image_ids AS (
        SELECT image
        FROM tagged
        WHERE tag in (SELECT id FROM tag_items)
        AND (created_at, image) >= ($3, $5)
        AND (created_at, image) < ($4, $5)
        GROUP BY image, created_at
        ORDER BY created_at DESC
        LIMIT $2
),
image_tag_ids AS (
        SELECT image, tag
        FROM tagged
        WHERE image in (SELECT image FROM image_ids)
),
image_tags AS (
        SELECT image, string_agg(tags.name, ',') as tags
        FROM image_tag_ids
        LEFT JOIN tags
        ON image_tag_ids.tag = tags.id
        GROUP BY image
),
image_tags_full_info AS (
        SELECT images.*, image_tags.tags
        FROM image_tags
        LEFT JOIN images
        ON image_tags.image = images.id
        ORDER BY images.created_at DESC
)
SELECT * FROM image_tags_full_info
"""
