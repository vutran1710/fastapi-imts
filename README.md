# Image-Tagged-System


## Setup
Copy **docker-local.env** to your own **.env** file, installing project dependencies and start docker-compose.
```
$ cp docker-local.env .env
$ pipenv install --dev --pre
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

| Prefix   | Endpoint       | Method | Params                                      | Authenticated | Data                   | Description                                 |
|----------|----------------|--------|---------------------------------------------|---------------|------------------------|---------------------------------------------|
| v1/image |                | POST   | NO                                          | YES           | FormData[image, tags]  | Upload image file, and tags                 |
|          | /              | GET    | image_id, limit, offset, from_time, to_time | YES           |                        | Get a single image or fetch multiple images |



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
