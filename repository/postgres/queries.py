"""Posgres SQL Plain Queries
Written to work with asyncpg
"""

FIND_USER_BY_EMAIL = "SELECT * FROM users WHERE email = $1"

FIND_USER_BY_ID = "SELECT * FROM users WHERE id = $1"

REGISTER_NEW_USER_APP = """
INSERT INTO users (id, email, password, provider)
VALUES ($1, $2, $3, 'app')
ON CONFLICT DO NOTHING
RETURNING *
"""

REGISTER_NEW_USER_SOCIAL = """
INSERT INTO users (id, email, token, expire_at, provider)
VALUES ($1, $2, $3, $4, $5)
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

FIND_IMAGE_BY_ID = "SELECT * FROM images WHERE id = $1"

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

SEARCH_TAGGED_IMAGES_BY_TAGS = """
WITH tag_ids AS (
        SELECT id
        FROM tags
        WHERE name IN (SELECT r.name FROM unnest($1::tags[]) as r)
     ),

     tag_image_ids AS (
        SELECT image, created_at
        FROM tagged
        WHERE tag IN (SELECT id FROM tag_ids)
        AND created_at >= $2 AND created_at <= $3
        ORDER BY created_at DESC LIMIT $4 OFFSET $5
     )
SELECT images.*
FROM images
RIGHT JOIN tag_image_ids ON tag_image_ids.image = images.id
ORDER BY images.created_at DESC
"""

GET_TAGS_FOR_MULTIPLE_IMAGES = """
WITH image_tag AS (
         SELECT *
         FROM tagged
         WHERE image
         IN (SELECT r.image FROM unnest($1::tagged[]) as r)
     ),
     image_tag_name AS (
         SELECT image_tag.image, tags.name
         FROM image_tag
         LEFT JOIN tags ON image_tag.tag = tags.id
     )
SELECT image, string_agg(name, ',') AS tags
FROM image_tag_name
GROUP BY image
"""