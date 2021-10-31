# Image-Tagged-System


## Setup
Installing everything
```
$ pipenv install --dev --pre
$ cp docker-local.env .env
$ docker-compose up -d
$ pipenv run dev
```

## System overview
### Components
1. **FastAPI** backend
1. **PostgreSQL** for data persistence
1. **MongoDB** for log/metric collection
1. **Minio** for image storing
1. **Redis** for caching / optimizing request/response *(not implemented for now)*

### Persistent data schema design
#### User
| COLUMN_NAME | COLUMN_TYPE | COLUMN_DEFAULT | IS_NULLABLE | COLUMN_KEY | EXTRA/CONSTRAINT | COLUMN_COMMENT                 |
|-------------|-------------|----------------|-------------|------------|------------------|--------------------------------|
| id          | uuid4       | NULL           | NO          | PRI        |                  | ID                             |
| email       | varchar     | NULL           | NO          |            | UNIQUE           |                                |
| password    | varchar     | NULL           | YES         |            |                  | Null if user uses social-login |
| token       | varchar     | NULL           | YES         |            | UNIQUE           | for social-login only          |
| expire_at   | timestamp   | NULL           | YES         |            |                  | for social-login only          |
| created_at  | timestamp   | NOW            | NO          |            |                  | registration time              |

#### Images
| COLUMN_NAME | COLUMN_TYPE | COLUMN_DEFAULT | IS_NULLABLE | COLUMN_KEY | EXTRA/CONSTRAINT | COLUMN_COMMENT                      |
|-------------|-------------|----------------|-------------|------------|------------------|-------------------------------------|
| id          | uuid1       | NULL           | NO          | PRI        |                  | ID                                  |
| name        | varchar     | NULL           | NO          |            | UNIQUE           | image's original file name          |
| storage_key | varchar     | NULL           | NO          |            |                  | Key used to store image on S3/Minio |
| created_at  | timestamp   | NOW            | NO          |            |                  | upload time                         |
| uploaded_by | uuid4       | NULL           | YES         | FOREIGN    |                  | Ref to user table                   |

#### Tags
| COLUMN_NAME | COLUMN_TYPE | COLUMN_DEFAULT | IS_NULLABLE | COLUMN_KEY | EXTRA/CONSTRAINT | COLUMN_COMMENT |
|-------------|-------------|----------------|-------------|------------|------------------|----------------|
| id          | serial      | NULL           | NO          | PRI        |                  | ID             |
| name        | varchar     | NULL           | NO          |            | UNIQUE           | tag name       |

#### Tagged
| COLUMN_NAME | COLUMN_TYPE | COLUMN_DEFAULT | IS_NULLABLE | COLUMN_KEY         | EXTRA/CONSTRAINT | COLUMN_COMMENT          |
|-------------|-------------|----------------|-------------|--------------------|------------------|-------------------------|
| tag         | integer     | NULL           | NO          | FOREIGN, COMPOSITE | UNIQUE           | Ref to Tags(id) table   |
| image       | uuid1       | NULL           | NO          | FOREIGN, COMPOSITE | UNIQUE           | Ref to Images(id) table |
| created_at  | timestamp   | NOW            | NO          |                    |                  | upload time             |
