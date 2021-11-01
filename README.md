# Image-Tagged-System

- [Setup](#setup)
- [System overview](#system-overview)
  - [Components](#components)
  - [Persistent data schema design](#persistent-data-schema-design)
    - [User](#user)
    - [Images](#images)
    - [Tags](#tags)
    - [Tagged](#tagged)
  - [Features & API Endpoints](#features--api-endpoints)
- [User/API-consumer tracking](#userapi-consumer-tracking)
- [Development Guideline](#development-guideline)
  - [Writing code, linting & format](#writing-code-linting--format)
  - [Testing, code-coverage](#testing-code-coverage)
- [TODO](#todo)

## Setup
Copy **docker-local.env** to your own **.env** file, installing project dependencies and start docker-compose.
```
$ cp docker-local.env .env
$ pipenv install --dev --pre
$ docker-compose up -d
$ pipenv run dev
```

## System overview

This is a FastAPI example application, made for future used as a template/starting point to develop more complex applications.
The app is made to storing/searching images with relevant tags.

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
| name        | varchar     | NULL           | NO          |            |                  | image's original file name          |
| storage_key | varchar     | NULL           | NO          |            | UNIQUE           | Key used to store image on S3/Minio |
| created_at  | timestamp   | NOW            | NO          |            |                  | upload time                         |
| uploaded_by | uuid4       | NULL           | YES         | FOREIGN    |                  | Ref to user table                   |

#### Tags
| COLUMN_NAME | COLUMN_TYPE | COLUMN_DEFAULT | IS_NULLABLE | COLUMN_KEY | EXTRA/CONSTRAINT | COLUMN_COMMENT |
|-------------|-------------|----------------|-------------|------------|------------------|----------------|
| id          | serial      | NULL           | NO          | PRI        |                  | ID             |
| name        | varchar     | NULL           | NO          |            | UNIQUE           | tag name       |

#### Tagged
| COLUMN_NAME | COLUMN_TYPE | COLUMN_DEFAULT | IS_NULLABLE | COLUMN_KEY         | EXTRA/CONSTRAINT | COLUMN_COMMENT                                                          |
|-------------|-------------|----------------|-------------|--------------------|------------------|-------------------------------------------------------------------------|
| tag         | integer     | NULL           | NO          | FOREIGN, COMPOSITE |                  | Ref to Tags(id) table                                                   |
| image       | uuid1       | NULL           | NO          | FOREIGN, COMPOSITE |                  | Ref to Images(id) table                                                 |
| created_at  | timestamp   | NOW            | NO          |                    |                  | upload time, same as image's created_at, to help boost find-image query |


- Refer to **Pydantic Model** in *model/postgres.py*




### Features & API Endpoints
FastAPI provides Swagger with OpenAPI. To use the API, simply run the backend with command..

```
$ pipenv run dev
```

...and go to http://localhost:8000/docs

--

User registration and authentication with both **email/password** or using social-login with **Facebook** and **Google**

| Prefix  | Endpoint       | Method | Params | Authenticated | Data                      | Description                    |
|---------|----------------|--------|--------|---------------|---------------------------|--------------------------------|
| v1/auth | /sign-up       | POST   | NO     | NO            | FormData[email, password] | Sign up using email & password |
|         | /login         | POST   | NO     | NO            | FormData[email, password] | Login using email & password   |
|         | /refresh-token | GET    | NO     | YES           |                           | Exchange JWT Token             |
|         | /facebook      | POST   | NO     | NO            | Facebook login payload    | Signup/Login with facebook     |
|         | /google        | POST   | NO     | NO            | Google login payload      | Signup/Login with Google       |



Image upload, fetching, searching

| Prefix   | Endpoint | Method | Params                                      | Authenticated | Data                  | Description                                 |
|----------|----------|--------|---------------------------------------------|---------------|-----------------------|---------------------------------------------|
| v1/image |          | POST   | NO                                          | YES           | FormData[image, tags] | Upload image file, and tags                 |
|          | /find    | GET    | image_id, limit, offset, from_time, to_time | YES           |                       | Get a single image or fetch multiple images |



Tag creation

| Prefix | Endpoint | Method | Params | Authenticated | Data            | Description                 |
|--------|----------|--------|--------|---------------|-----------------|-----------------------------|
| v1/tag |          | POST   | NO     | YES           | {tag: string[]} | Upload image file, and tags |


## User/API-consumer tracking
Authenticated User or API-consumer will have their every sent request info save to **MongoDB** > **tracking_users** collection for future statistic / analysing


## Development Guideline

### Writing code, linting & format
- Code format complies with **Black**. Auto-format everything with..
```
$ pipenv run format
```

- **Radon** is used to ensure high readability, in conjunction with **flake8** complex level (maximum  4). Check for code-complexity using...
```
$ pipenv run flake
```

- **imports** are arranged automatically with **isort**. Fix sorting issues with...
```
$ pipenv run sort
```

- Strict typing with **mypy**. Check for typing errors with
```
$ pipenv run type
```




### Testing, code-coverage
Testing is done with **pytest**. Run the full test suite with
```
$ pipenv run test
```


Coverage report format is set as `html`. After having finish the test run, go to *htmlcov/index.html* to view test report.

#### Up-to-date coverage
```
Name                             Stmts   Miss  Cover
----------------------------------------------------
api/auth/router.py                  50     13    74%
api/image/router.py                 51      3    94%
api/tags/router.py                  13      0   100%
libs/dependencies.py                31      0   100%
libs/exceptions.py                  13      0   100%
libs/jwt.py                         23      0   100%
libs/utils.py                       49      2    96%
main.py                              9      0   100%
model/auth.py                       27      0   100%
model/enums.py                       2      0   100%
model/http.py                       50      6    88%
model/metrics.py                     8      0   100%
model/postgres.py                   26      0   100%
repository/dependencies.py          37     13    65%
repository/http.py                  16      9    44%
repository/metric_collector.py      25      0   100%
repository/minio.py                 28      2    93%
repository/postgres/connect.py      86      0   100%
repository/postgres/queries.py      13      0   100%
repository/redis.py                 11      4    64%
settings.py                         30      0   100%
----------------------------------------------------
TOTAL                              598     52    91%
```


## TODO
- [ ] Change user'id and image'id to int
- [ ] Add logout API to invalidate user token
- [ ] Provide **Dockerfile**
- [ ] Provide API for adding tags for existing image
- [ ] Create *Index* on uploaded_by of table **Images** to support searching images by user
- [ ] Refactor Query Response following *snowflake* pattern to provide better pagination
- [ ] Provide *migration* script
- [ ] Provide *pytest-postgresql* for better testing
- [ ] Allow making images private by author
- [ ] Stress-testing and optimizing if needed
