# DRF Bookstore (Portfolio / Demo)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

An opinionated **Django REST Framework** bookstore API that showcases real-world API design: nested resources (book reviews), role-based permissions (admin / manager / delivery / customer), robust validation (ISBN, address uniqueness), derived fields (discounted price, average rating), filtering/search/order, pagination, throttling by role, and audit trails (order history).

> This repository is **demo/portfolio** grade — great for code review, local testing, and discussing architecture. It is not intended for direct production use.

---

## Table of contents

- [DRF Bookstore (Portfolio / Demo)](#drf-bookstore-portfolio--demo)
  - [Table of contents](#table-of-contents)
  - [Features](#features)
  - [Tech stack](#tech-stack)
  - [Project structure](#project-structure)
  - [Environments \& how to run](#environments--how-to-run)
    - [Quickstart (Demo mode)](#quickstart-demo-mode)
        - [0. (Optional) set up a .env](#0-optional-set-up-a-env)
        - [1. Install dependencies](#1-install-dependencies)
        - [2. Run migrations \& load seed data](#2-run-migrations--load-seed-data)
        - [3. Run the server](#3-run-the-server)
    - [“Prod-like” locally](#prod-like-locally)
    - [Windows quickstart (PowerShell)](#windows-quickstart-powershell)
  - [How to use the API (tools, formats, and conventions)](#how-to-use-the-api-tools-formats-and-conventions)
      - [Base URL \& versions](#base-url--versions)
      - [Authentication header (JWT)](#authentication-header-jwt)
      - [Common headers](#common-headers)
      - [Browsable API (HTML)](#browsable-api-html)
      - [Response formats (content negotiation)](#response-formats-content-negotiation)
      - [Pagination, filtering, search, ordering](#pagination-filtering-search-ordering)
      - [Error shapes](#error-shapes)
      - [Tools you can use](#tools-you-can-use)
      - [Notes](#notes)
  - [Authentication](#authentication)
      - [Register a user (Djoser)](#register-a-user-djoser)
      - [Obtain tokens (SimpleJWT)](#obtain-tokens-simplejwt)
      - [Call an authenticated endpoint](#call-an-authenticated-endpoint)
      - [Refresh the access token](#refresh-the-access-token)
      - [Log out / revoke (blacklist) the refresh token](#log-out--revoke-blacklist-the-refresh-token)
  - [Roles \& permissions](#roles--permissions)
  - [Managing employee groups (Admin/Manager tools)](#managing-employee-groups-adminmanager-tools)
      - [Auth header](#auth-header)
      - [A) Manager group](#a-manager-group)
      - [B) Delivery group](#b-delivery-group)
      - [Tips](#tips)
  - [Throttling](#throttling)
  - [Pagination](#pagination)
  - [API reference](#api-reference)
    - [Taxonomies (read-only): Genre, Stock, BookFormat, OrderStatus, Country](#taxonomies-read-only-genre-stock-bookformat-orderstatus-country)
    - [Books](#books)
      - [Examples](#examples)
    - [Reviews (nested under Books)](#reviews-nested-under-books)
    - [Cart](#cart)
      - [Examples](#examples-1)
    - [Addresses](#addresses)
    - [Orders](#orders)
      - [Creating an order](#creating-an-order)
      - [Updating an order (rules by role)](#updating-an-order-rules-by-role)
    - [Order Items (by order)](#order-items-by-order)
    - [Order History (by order)](#order-history-by-order)
  - [Filtering \& search summary](#filtering--search-summary)
  - [Validation highlights](#validation-highlights)
  - [Error shapes](#error-shapes-1)
  - [FAQ / troubleshooting](#faq--troubleshooting)
  - [License](#license)
    - [Notes for reviewers](#notes-for-reviewers)

---

## Features

- **Nested resources**: `/books/:book_id/reviews`
- **Role-driven access**: admin / manager / delivery / customer
- **Strong validation**: ISBN10/13, address uniqueness, order transitions, safe HTML sanitation
- **Derived fields**: `price` (after discount), `average_rating`, formatted dates, helpful “list_url”
- **Query power**: filtering ranges (numeric/date), min/max price via queryset annotations, search & ordering
- **Audit & status flow**: order history entries + allowed status transitions per role
- **Throttling by role**: manager/delivery/customer/anon with separate limits
- **JWT + Djoser installed** for easy auth (obtain/refresh tokens, basic user flows)

---

## Tech stack

- **Python / Django 5**
- **Django REST Framework**
- **django-filters**
- **DRF SimpleJWT** (access/refresh; rotation enabled)
- **Djoser** (user endpoints; `USER_ID_FIELD='username'`)
- SQLite by default for easy local runs

---

## Project structure

```
.
├── config
│   ├── settings
│   │   ├── base.py          # shared defaults (DEBUG=False, safe defaults)
│   │   ├── demo.py          # local/demo toggles (DEBUG=True, console email)
│   │   └── prod.py.sample   # production-like hardening template
│   └── urls.py              # mounts /api/, /api/store/, reviews
├── store/                   # bookstore domain: books, cart, orders, addresses ...
├── reviews/                 # nested book reviews
├── fixtures/                # demo data (core.json, demo.json)
├── manage.py
└── README.md
```

> `demo.py` flips on DEV conveniences like `DEBUG=True`, `ALLOWED_HOSTS=["*"]`, and console email.

---

## Environments & how to run

This repo uses a tiny settings split:

- `config.settings.base` — shared defaults (**`DEBUG=False`**), reads secret from env with a **demo-only fallback** key
- `config.settings.demo` — local/demo (**`DEBUG=True`**, permissive hosts, console email)
- `config/settings/prod.py.sample` — prod-like hardening template you can copy to `prod.py` for local testing

Environment variables in `.env.example` include a convenient default for demo and commented examples for prod-like runs.

### Quickstart (Demo mode)

##### 0. (Optional) set up a .env
```bash
# sets DJANGO_SETTINGS_MODULE=config.settings.demo
cp .env.example .env
```


##### 1. Install dependencies

You can use **pipenv** (recommended):
```bash

pip install pipenv # if not already installed
pipenv install --dev
pipenv shell
```
Or plain **pip/venv**:
```bash
python -m venv .venv
source .venv/bin/activate     # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
```



##### 2. Run migrations & load seed data

We ship three fixtures with different priorities:

1. `fixtures/core.json` **(mandatory)**  
   Base taxonomies and statuses required by the API. This also defines the user groups.

2. `fixtures/demo_users.json` **(optional)**  
   Preconfigured demo users and sample addresses.

3. `fixtures/demo.json` **(optional, recommended)**  
   Books, plus example reviews.

**Load order:**
```bash
python manage.py migrate
python manage.py loaddata fixtures/core.json
python manage.py loaddata fixtures/demo_users.json   # optional
python manage.py loaddata fixtures/demo.json         # recommended
```

If you skip **demo_users.json**, you'll need to create users manually (via the admin panel or the API) and assign some of them to the **manager** and the **delivery** groups to unlock all role-based flows.  

To create a superuser:

```bash
python manage.py createsuperuser
```

You'll be prompted to enter a username (e.g. *admin*) and a password. 
Other users can be created and assigned to groups either via the admin panel at http://127.0.0.1:8000/admin/ or through the dedicated API endpoints described later in this README. Another API endpoint allows you to create shipping addresses for customers who will place orders. 

If you did load **demo_users.json**, you can skip creating a superuser manually - it already includes one, along with other preconfigured accounts. You’re still free to add new users, assign them to groups, or manage addresses as needed.

**Demo credentials** (from `demo_users.json`):

| Username   | Password        | Role              |
|------------|-----------------|-------------------|
| admin      | imthesuperuser  | Admin (superuser) |
| manager    | imveryimportant | Manager           |
| deliverer1 | igetthejobdone1 | Delivery          |
| deliverer2 | igetthejobdone2 | Delivery          |
| customer1  | 123&456w        | Customer          |
| customer2  | 456&789w        | Customer          |
| customer3  | 789&123w        | Customer          |


##### 3. Run the server
```bash
python manage.py runserver
```

### “Prod-like” locally

If you want to test with secure toggles (still on your laptop):

```bash
# 1) copy the hardened template
cp config/settings/prod.py.sample config/settings/prod.py

# 2) point to prod settings
export DJANGO_SETTINGS_MODULE=config.settings.prod

# 3) required env vars
export DJANGO_SECRET_KEY="$(python -c 'from django.core.management.utils import get_random_secret_key as g; print(g())')"
export DJANGO_ALLOWED_HOSTS="localhost,127.0.0.1"
export DJANGO_CSRF_TRUSTED="http://localhost:8000"

# 4) optional DB (else keep SQLite)
# export DATABASE_URL="postgres://user:pass@host:5432/dbname"

# 5) migrate & (optionally) load fixtures
python manage.py migrate
# Load base taxonomies
python manage.py loaddata fixtures/core.json
# Optionally load users and demo data
# python manage.py loaddata fixtures/demo_users.json
# python manage.py loaddata fixtures/demo.json

# 6) sanity check
python manage.py check --deploy

# 7) run
python manage.py runserver
```

The sample `prod.py` **enforces** a real secret key and sets secure defaults (HSTS, HTTPS assumptions, secure cookies). Never deploy with `demo.py`.

### Windows quickstart (PowerShell)

```powershell
Copy-Item .env.example .env

py -m venv .venv
.\.venv\Scripts\Activate.ps1

pip install -r requirements.txt

# Demo settings for this shell only (if you didn't copy .env)
$env:DJANGO_SETTINGS_MODULE = "config.settings.demo"

python manage.py migrate
python manage.py loaddata .\fixtures\core.json
# Optional:
# python manage.py loaddata .\fixtures\demo_users.json
# python manage.py loaddata .\fixtures\demo.json

# If you skipped demo_users.json, create an admin:
# python manage.py createsuperuser

python manage.py runserver
```

**Prod-like on PowerShell:**

```powershell
Copy-Item .\config\settings\prod.py.sample .\config\settings\prod.py
$env:DJANGO_SETTINGS_MODULE = "config.settings.prod"
$env:DJANGO_SECRET_KEY = (python -c "from django.core.management.utils import get_random_secret_key as g; print(g())")
$env:DJANGO_ALLOWED_HOSTS = "localhost,127.0.0.1"
$env:DJANGO_CSRF_TRUSTED = "http://localhost:8000"

python manage.py migrate
python manage.py loaddata .\fixtures\core.json
# Optional:
# python manage.py loaddata .\fixtures\demo_users.json
# python manage.py loaddata .\fixtures\demo.json

python manage.py check --deploy
python manage.py runserver
```

Common mappings: `cp` → `Copy-Item`; `export VAR=value` → `$env:VAR = "value"`.

---
## How to use the API (tools, formats, and conventions)

You can exercise the API using **curl** (all examples in this README use curl), or with GUI tools like **Postman** and **Insomnia**. DRF also provides a browsable API (HTML) that’s handy for quickly inspecting payloads and trying requests from your browser.

#### Base URL & versions

- Base URL (local): http://127.0.0.1:8000

- API roots:

  - Auth & tokens:`/api/…`

  - Store domain: `/api/store/…`

- Example: GET `/api/store/books`

#### Authentication header (JWT)

Most endpoints require a Bearer token:

```bash
-H "Authorization: Bearer <ACCESS_TOKEN>"
```


Get tokens in the [Authentication](#authentication) section (register → obtain → refresh).

#### Common headers

```bash
-H "Content-Type: application/json"    # for requests with a body
-H "Accept: application/json"          # default API response
```

#### Browsable API (HTML)

Every endpoint can return a human-friendly HTML page (DRF’s browsable API). Use your web browser:

- Visit http://127.0.0.1:8000/api/store/books to browse list/detail pages.

- You can inspect fields and (where allowed) submit forms.

- If you want to fetch the HTML version via curl, set the Accept header:

```bash
curl -i http://127.0.0.1:8000/api/store/books \
  -H "Accept: text/html"
```

>Notes:
>- The browsable API is great for discovery. For authenticated actions with JWT, curl/Postman/Insomnia is usually easier because you control the `Authorization` header directly.

#### Response formats (content negotiation)

DRF honors Accept:

- `application/json` → JSON (default in our examples)

- `text/html` → DRF browsable API

#### Pagination, filtering, search, ordering

- Pagination: page-number pagination (`?page=N`) with standard DRF shape (`count`, `next`, `previous`, `results`).

- Filtering: use query params like `?genre=2&price_max=12.99` (see the [Filtering & search summary table](#filtering--search-summary)).

- Search: `?search=<text>`.

- Ordering: `?ordering=price` or ?`ordering=-price`.

#### Error shapes

You’ll get standard DRF errors (JSON), e.g.:

```json
{ "detail": "You do not have permission to perform this action." }
```

Field-level validation errors are arrays keyed by field name.

#### Tools you can use

- **curl** (shown in this README — scriptable, universal)

- **HTTPie**: nice ergonomics for quick tests

- **Postman** / **Insomnia**: import requests, save environments, share collections

We stick to **curl** in all examples below for consistency. If you prefer Postman/Insomnia, copy the same URL, headers, and JSON bodies.


#### Notes
- **Only JWT auth endpoints (`/api/token/…`, djoser `/api/auth/…`) use trailing slashes**
- All other API endpoints **do not have trailing slashes**

--- 

## Authentication

**Installed**: DRF SimpleJWT (token model) + Djoser (user endpoints).

- **Auth base paths** (as wired in `config/urls.py`):
  - **Djoser**: `/api/auth/` (e.g., `/api/auth/users/`, etc.)
  - **JWT**:
    - `POST /api/token/` → obtain access/refresh
    - `POST /api/token/refresh/` → rotate/refresh
    - `POST /api/token/blacklist/` → revoke refresh token

All application endpoints accept `Authorization: Bearer <token>` for authenticated flows.

Token lifetimes (defaults): access 15 minutes, refresh 1 day. Rotation and blacklisting are enabled.



#### Register a user (Djoser)

```bash
curl -X POST http://127.0.0.1:8000/api/auth/users/ \
  -H "Content-Type: application/json" \
  -d '{
    "username": "alice",
    "password": "AliceStrongPass123!",
    "email": "alice@example.com"
  }'
```

>Notes:
>- In this demo setup, accounts are usable right after creation. (Production setups may require email verification.)
>- You can also create users via Django admin at `/admin/`.



#### Obtain tokens (SimpleJWT)

```bash
curl -X POST http://127.0.0.1:8000/api/token/ \
  -H "Content-Type: application/json" \
  -d '{
    "username": "alice",
    "password": "AliceStrongPass123!"
  }'
```



**Example response:**

```json
{
  "refresh": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1...",
  "access":  "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1..."
}
```

Save both tokens. Use the **access** token in the `Authorization` header for subsequent requests.



#### Call an authenticated endpoint

**Example: list items in your cart**

```bash
ACCESS="<paste access token>"

curl -X GET http://127.0.0.1:8000/api/store/cart/items \
  -H "Authorization: Bearer $ACCESS"
```


#### Refresh the access token

When the access token expires, use the **refresh** token to get a new access token:

```bash
REFRESH="<paste refresh token>"

curl -X POST http://127.0.0.1:8000/api/token/refresh/ \
  -H "Content-Type: application/json" \
  -d "{\"refresh\": \"$REFRESH\"}"
```



**Example response (200):**

```json
{
  "refresh": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1...",
  "access":  "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1..."
}
```

>After refreshing, the old refresh token can’t be used anymore. (This project enables token rotation + blacklisting.)



#### Log out / revoke (blacklist) the refresh token

```bash
REFRESH="<paste refresh token>"

curl -X POST http://127.0.0.1:8000/api/token/blacklist/ \
  -H "Content-Type: application/json" \
  -d "{\"refresh\": \"$REFRESH\"}"
```


>After blacklisting, that refresh token can’t be used anymore. A new pair of tokens must be generated again through the designated endpoint.

---

## Roles & permissions

Roles are inferred by superuser/group membership:

- **admin** → Django superuser
- **manager**, **delivery** → membership in groups with those names
- default → **customer** (any authenticated user); **anonymous** for non-auth

Selected endpoints enforce **object-level** permissions (e.g., only cart/address owners may update; managers can view carts but not modify; admins can do more). 

---

## Managing employee groups (Admin/Manager tools)

Two helper endpoints let you add/remove users to the **manager** and **delivery** groups.
They accept/return JSON and require an authenticated user with the right role:

- **Manager group**

  - `GET /api/store/groups/manager/users` — list members (**admin only**)

  - `POST /api/store/groups/manager/users` — add user (**admin only**)

  - `DELETE /api/store/groups/manager/users` — remove user (**admin only**)

- **Delivery group**

  - `GET /api/store/groups/delivery/users` — list members (**admin or manager**)

  - `POST /api/store/groups/delivery/users` — add user (**admin or manager**)

  - `DELETE /api/store/groups/delivery/users` — remove user (**admin or manager**)

>**Why it matters:**
>- Users in **manager** can create/update/delete books, view all carts/orders, and manage delivery group membership.
>- Users in **delivery** can update delivery-related order statuses on assigned orders.
>- Customers (**no groups**) can shop, manage their cart, addresses, place orders, and request cancellations/refunds as allowed.



#### Auth header

All requests below assume:

```bash
ACCESS="<admin or manager access token>"
```



#### A) Manager group

**List manager users (admin only)**

```bash
curl -X GET http://127.0.0.1:8000/api/store/groups/manager/users \
  -H "Authorization: Bearer $ACCESS"
```



**Add a user to manager (admin only)**

```bash
curl -X POST http://127.0.0.1:8000/api/store/groups/manager/users \
  -H "Authorization: Bearer $ACCESS" \
  -H "Content-Type: application/json" \
  -d '{"username":"manager"}'
```


**Remove a user from manager (admin only)**

```bash
curl -X DELETE http://127.0.0.1:8000/api/store/groups/manager/users \
  -H "Authorization: Bearer $ACCESS" \
  -H "Content-Type: application/json" \
  -d '{"username":"manager"}'
```



#### B) Delivery group

**List delivery users (admin or manager)**

```bash
curl -X GET http://127.0.0.1:8000/api/store/groups/delivery/users \
  -H "Authorization: Bearer $ACCESS"
```



**Add a user to delivery (admin or manager)**

```bash
curl -X POST http://127.0.0.1:8000/api/store/groups/delivery/users \
  -H "Authorization: Bearer $ACCESS" \
  -H "Content-Type: application/json" \
  -d '{"username":"deliverer1"}'
```



**Remove a user from delivery (admin or manager)**

```bash
curl -X DELETE http://127.0.0.1:8000/api/store/groups/delivery/users \
  -H "Authorization: Bearer $ACCESS" \
  -H "Content-Type: application/json" \
  -d '{"username":"deliverer1"}'
```



#### Tips

- To test end-to-end quickly, load `fixtures/demo_users.json` so you already have an admin, manager, delivery, and customer accounts ready to go.

- You can always promote/demote users using the endpoints above or via Django admin.


---

## Throttling

Global defaults (per `REST_FRAMEWORK`):

- `anon`: `30/minute`
- `user`: `120/minute`
- role scopes:
  - `customer`: `600/hour`
  - `manager`: `2000/hour`
  - `delivery`: `1000/hour`

Viewsets delegate to a helper that picks the appropriate throttle class list for the current user (admins/managers get roomier limits where needed).

---

## Pagination

- Page number pagination with `PAGE_SIZE = 4`.
- Standard DRF shape:

```json
{
  "count": 23,
  "next": "http://localhost:8000/api/store/books?page=3",
  "previous": "http://localhost:8000/api/store/books?page=1",
  "results": [ ...items... ]
}
```

Search, ordering, and filtering backends are enabled framework-wide.

---

## API reference

>**Routing note**: Unless otherwise specified, endpoints here are shown without **trailing slashes**.

### Taxonomies (read-only): Genre, Stock, BookFormat, OrderStatus, Country

**Why this matters:** You’ll need these IDs when creating books, addresses, and orders.

- `GET /genres`, `GET /genres/<id>`
- `GET /stocks`, `GET /stocks/<id>`
- `GET /book-formats`, `GET /book-formats/<id>`
- `GET /order-statuses`, `GET /order-statuses/<id>`
- `GET /countries`, `GET /countries/<id>`

**Permissions:** public read.

**Schemas:** each exposes `id`, `title`, `slug` and (where applicable) hyperlinked URLs.



**Example: list genres (public)**

```bash
curl -X GET http://127.0.0.1:8000/api/store/genres
```



**Example response (200, trimmed)**

```json
[
  { "id": 1, "url": "http://127.0.0.1:8000/api/store/genres/1", "title": "Science Fiction", "slug": "science-fiction" },
  { "id": 2, "url": "http://127.0.0.1:8000/api/store/genres/2", "title": "Fantasy", "slug": "fantasy" }
]
```

>**Note**: These resources are **read-only via API** in this project. Create/update them via fixtures (```fixtures/core.json```) or **Django admin**.

---

### Books

**Endpoints**

- `GET /books` — list (with derived fields)
- `POST /books` — create (**admin/manager**)
- `GET /books/<id>` — retrieve
- `PUT/PATCH /books/<id>` — update (**admin/manager**)
- `DELETE /books/<id>` — delete (**admin/manager**); fails cleanly if referenced by orders

**Fields (selected)**

- Core: `title`, `author`, `genre`, `publisher`, `edition`, `language`, `book_format`, `isbn`, `is_new`, `stock`, `baseprice`, `discount`, `first_publication_year`, `is_bc`, `blurb`
- **Derived in responses**:
  - `price` (computed: `baseprice * (100 - discount)/100`)
  - `average_rating` (reviews aggregate)
  - `publication_year` (string; “BC” suffix when relevant)
  - Links: `genre_url`, `book_format_url`, `stock_url`, `reviews_url`, `list_url`, `add_to_cart_info`

**Search & ordering**

- `?search=` over `title`, `author`, `genre__title`, `publisher`
- `?ordering=` over `author`, `title`, `edition`, `price`, `discount` (prefix `-` for desc)

**Filters**

- Exact: `genre`, `book_format`, `language`, `is_new`, `stock`
- Ranges:
  - `discount_gte`, `discount_lte`
  - `first_publication_year_gte`, `first_publication_year_lte`
  - **Price annotation**: `price_min`, `price_max`
  - **Rating annotation**: `rating_min`, `rating_max`
  - `is_bc` (boolean)


**Deletion safety**

- Deleting a book referenced by orders returns a validation error with a helpful message.



#### Examples

**List books (public)**

```bash
curl -X GET http://127.0.0.1:8000/api/store/books
```



**Example response (200, trimmed)**

```json
{
	"count": 2,
	"next": null,
	"previous": null,
	"results": [
		{
			"id": 4,
			"title": "To Kill a Mockingbird",
			"author": "Harper Lee",
			"genre_display": "Novel",
			"edition": 1,
			"book_format_display": "Paperback",
			"price": 12.74,
			"average_rating": 4.5,
			"url": "http://127.0.0.1:8000/api/store/books/4"
		},
		{
			"id": 12,
			"title": "The Catcher in the Rye",
			"author": "J. D. Salinger",
			"genre_display": "Novel",
			"edition": 1,
			"book_format_display": "Paperback",
			"price": 10.99,
			"average_rating": null,
			"url": "http://127.0.0.1:8000/api/store/books/12"
		}
  ]
}
```



**Get details from book with id = 4 (public)**

```bash
curl -X GET http://127.0.0.1:8000/api/store/books/4
```



**Example response (200)**

```json
{
    "id": 4,
    "title": "To Kill a Mockingbird",
    "author": "Harper Lee",
    "genre_display": "Novel",
    "genre_url": "http://127.0.0.1:8000/api/store/genres/1",
    "publication_year": "1960",
    "blurb": "A novel of childhood, justice, and conscience in the American South.",
    "publisher": "Harper Perennial Modern Classics",
    "edition": 1,
    "language": "English",
    "book_format_display": "Paperback",
    "book_format_url": "http://127.0.0.1:8000/api/store/book-formats/1",
    "isbn": "9780061120084",
    "is_new": true,
    "stock_display": "In Stock",
    "stock_url": "http://127.0.0.1:8000/api/store/stocks/1",
    "baseprice": "14.99",
    "price": 12.74,
    "average_rating": 4.5,
    "discount": 15,
    "list_url": "Back to list: http://127.0.0.1:8000/api/store/books",
    "add_to_cart_info": {
        "url": "http://127.0.0.1:8000/api/store/cart/items",
        "method": "POST",
        "body": {
            "book": 4,
            "quantity": "<integer>"
        }
    },
    "reviews_url": "http://127.0.0.1:8000/api/store/books/4/reviews"
}
```




**Create a book (admin/manager)**

```bash
curl -X POST http://127.0.0.1:8000/api/store/books \
  -H "Authorization: Bearer <ACCESS_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Foundation",
    "author": "Isaac Asimov",
    "genre": 1,
    "publisher": "Gnome Press",
    "edition": 1,
    "language": "English",
    "book_format": 1,
    "isbn": "978-0-553-80371-0",
    "is_new": true,
    "stock": 1,
    "baseprice": "12.99",
    "discount": 23,
    "first_publication_year": 1951,
    "is_bc": false,
    "blurb": "A sci-fi classic about the fall of a galactic empire."
  }'
```


---

### Reviews (nested under Books)

**Endpoints**

- `GET /books/:book_id/reviews` — list + filters
- `POST /books/:book_id/reviews` — create (**auth required**)
- `GET /books/:book_id/reviews/<id>` — retrieve
- `PUT/PATCH /books/:book_id/reviews/<id>` — update (**author only**)
- `DELETE /books/:book_id/reviews/<id>` — delete (**author or admin**)

**Filters & ordering**

- Ranges: `rating_gte`, `rating_lte`
- Date ranges: `created_at_gte|_lte`, `updated_at_gte|_lte`
- `?search=user__username`
- `?ordering=rating|created_at|updated_at` (prefix `-` for desc)

**Notes**

- Enforces nested integrity: a review must belong to the `book_id` segment.
- Only one review per `(user, book)`.



**List all reviews for book with id = 4 (public)**

```bash
curl -X GET http://127.0.0.1:8000/api/store/books/4/reviews
```


**Example response (200)**

```json
{
    "count": 2,
    "next": null,
    "previous": null,
    "results": [
        {
            "id": 15,
            "customer": "customer2",
            "book_display": "To Kill a Mockingbird, by Harper Lee",
            "book_url": "http://127.0.0.1:8000/api/store/books/4",
            "rating": 5,
            "title": "Still essential",
            "comment": "Scout’s voice, Atticus’s quiet courage—every reread lands differently as I age.",
            "created_at": "2025-06-01T11:23:00+00:00",
            "url": "http://127.0.0.1:8000/api/store/books/4/reviews/15"
        },
        {
            "id": 16,
            "customer": "customer3",
            "book_display": "To Kill a Mockingbird, by Harper Lee",
            "book_url": "http://127.0.0.1:8000/api/store/books/4",
            "rating": 4,
            "title": "A classic with bite",
            "comment": "The courtroom chapters are electric; some pacing lulls outside them.",
            "created_at": "2024-05-13T08:02:00+00:00",
            "url": "http://127.0.0.1:8000/api/store/books/4/reviews/16"
        }
    ]
}
```



**Create a review for a book (auth)**

```bash
curl -X POST http://127.0.0.1:8000/api/store/books/7/reviews \
  -H "Authorization: Bearer <ACCESS_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "rating": 5,
    "title": "Classic!",
    "comment": "Still hits decades later."
  }'
```

---

### Cart

**Endpoints**

- `GET /cart/items` — list your cart
- `POST /cart/items` — add a book to your cart
- `DELETE /cart/items` — **flush** the entire cart (custom action)
- `GET /cart/items/<id>` — retrieve a cart line
- `PATCH /cart/items/<id>` — update **quantity only**
- `DELETE /cart/items/<id>` — remove a cart line

**Permissions**

- **Auth required**.
- **Owners & admins** can view/edit.
- **Managers** may **view** only (no edits).

**Validation & behavior**

- Adds with `book` (id) and `quantity` ≥ 1.
- Auto-calculates `unit_price` (discounted) and total `price`.
- Prevents adding `out-of-stock` or `discontinued` books.
- `PATCH` only accepts `quantity` — any other field triggers an error.
- List payload includes `other_info.cart_total` and “place order” helper (URL, method, expected body).

#### Examples

**Add a book to cart**

```bash
ACCESS="<paste access token>"

curl -X POST http://127.0.0.1:8000/api/store/cart/items \
  -H "Authorization: Bearer $ACCESS" \
  -H "Content-Type: application/json" \
  -d '{ "book": 6, "quantity": 2 }'
```



**List all books in your cart**

```bash
curl -X GET http://127.0.0.1:8000/api/store/cart/items \
  -H "Authorization: Bearer $ACCESS"
```



**Example response (200)**

```json
{
    "count": 2,
    "next": null,
    "previous": null,
    "results": [
        {
            "id": 18,
            "customer": "customer1",
            "book_display": "The Big Sleep, by Raymond Chandler",
            "book_url": "http://127.0.0.1:8000/api/store/books/6",
            "quantity": 2,
            "price": "25.12",
            "url": "http://127.0.0.1:8000/api/store/cart/items/1"
        },
        {
            "id": 19,
            "customer": "customer1",
            "book_display": "The Girl with the Dragon Tattoo, by Stieg Larsson",
            "book_url": "http://127.0.0.1:8000/api/store/books/2",
            "quantity": 1,
            "price": "15.20",
            "url": "http://127.0.0.1:8000/api/store/cart/items/2"
        }
    ],
    "other_info": {
        "cart_total": 40.32,
        "place_order_info": {
            "url": "http://127.0.0.1:8000/api/store/orders",
            "method": "POST",
            "body": {
                "delivery_address_id": "2 or 1"
            }
        }
    }
}
```



**Update book's quantity**
*(You must add the item's `id` in the URL)*

```bash
curl -X PATCH http://127.0.0.1:8000/api/store/cart/items/18 \
  -H "Authorization: Bearer $ACCESS" \
  -H "Content-Type: application/json" \
  -d '{ "quantity": 3 }'
```



**Flush your cart**

```bash
curl -X DELETE http://127.0.0.1:8000/api/store/cart/items \
  -H "Authorization: Bearer $ACCESS"
```


---

### Addresses

**Endpoints**

- `GET /addresses` — list your addresses (admins see all)
- `POST /addresses` — create
- `GET /addresses/<id>` — retrieve
- `PUT/PATCH /addresses/<id>` — update
- `DELETE /addresses/<id>` — delete

**Permissions**

- **Auth required**.
- **Owners** (and **admins**) may view/edit.

**Validation**

- Strict HTML sanitization on string fields.
- Uniqueness per `(user, recipient, country, zip_code, street_name, number)`.
  


**Example: list customer's addresses**

```bash
ACCESS="<paste customer's access token>"

curl -X GET http://127.0.0.1:8000/api/store/addresses \
  -H "Authorization: Bearer $ACCESS"
  ```



**Example response (200)**

```json
{
	"count": 2,
	"next": null,
	"previous": null,
	"results": [
		{
			"id": 2,
			"customer": "customer1",
			"recipient": "Alice Johnson",
			"country_info": {
				"id": 1,
				"title": "United Kingdom",
				"slug": "united-kingdom",
				"iso_3166": "826"
			},
			"country_url": "http://127.0.0.1:8000/api/store/countries/1",
			"state_province": "Cambridgeshire",
			"city_town": "Cambridge",
			"zip_code": "CB2 1HJ",
			"street_name": "Coronation St",
			"number": "60",
			"apartment_suite": "",
			"notes": "Leave package with neighbor if not home."
		},
		{
			"id": 1,
			"customer": "customer1",
			"recipient": "Alice Johnson",
			"country_info": {
				"id": 1,
				"title": "United Kingdom",
				"slug": "united-kingdom",
				"iso_3166": "826"
			},
			"country_url": "http://127.0.0.1:8000/api/store/countries/1",
			"state_province": "Sussex",
			"city_town": "Aldwick",
			"zip_code": "PO21 4BD",
			"street_name": "Pryors Ln",
			"number": "54",
			"apartment_suite": "Apt 4B",
			"notes": "Ring the buzzer marked 'Johnson'."
		}
	]
}
```



**Example: add an address**

```bash
curl -X POST http://127.0.0.1:8000/api/store/addresses \
  -H "Authorization: Bearer $ACCESS" \
  -H "Content-Type: application/json" \
  -d '{
    "recipient": "Charles Smith",
    "country": 1, 
    "state_province": "",
    "city_town": "London",
    "zip_code": "W11 1NW",
    "street_name": "Blenheim Cres",
    "number": "28",
    "apartment_suite": "",
    "notes": "Leave at the door."
  }'
```

---

### Orders

**Endpoints**

- `GET /orders` — list your orders
  - admins/managers see *all*
  - delivery sees *assigned to them*
  - customers see *their own*
- `POST /orders` — create from current user cart
- `GET /orders/<id>` — retrieve
- `PUT/PATCH /orders/<id>` — **controlled updates** (see rules)

#### Creating an order

- Request body needs `delivery_address` (id).
- Server collects current user cart items, computes total, creates `Order`, bulk-creates `OrderItem` rows, logs initial `OrderHistory`, **flushes the cart**, and returns the new `order_id`.

**Example**

```bash
ACCESS="<paste access token>"

curl -X POST http://127.0.0.1:8000/api/store/orders \
  -H "Authorization: Bearer $ACCESS" \
  -H "Content-Type: application/json" \
  -d '{ "delivery_address": 12 }'
```

#### Updating an order (rules by role)

- **Admins / Managers** may update: `status`, `deliverer`
- **Delivery** may update: `status`
- **Customers** may update: `delivery_address` *(only when `pending` or `failed`)*, and may set `intent` to **`cancellation`** or **`refund`** (enforces allowed origin status per intent)

**Status transitions (examples)**

- `pending → shipped` (admin/manager)
- `shipped → delivered` (admin/delivery)
- `any → under-review` under specific conditions
- invalid transitions are rejected with clear messages

**Business helpers**

- Assigning a `deliverer` early auto-moves status to `shipped`.
- Changing address in `failed` moves status to `under-review`.
- Setting an `intent` records a message and moves status to `under-review`.

**Timestamps**

- `when_placed` and `when_last_update` are localized in responses.

**Example: manager assigns a deliverer**
- **who**: admin or manager
- **effect**: sets `deliverer`; if current status is `pending` or `under-review`, it auto-sets status to `shipped`.

```bash
MANAGER_ACCESS="<manager access token>"

curl -X PATCH http://127.0.0.1:8000/api/store/orders/101 \
  -H "Authorization: Bearer $MANAGER_ACCESS" \
  -H "Content-Type: application/json" \
  -d '{ "deliverer": 6 }'    # user id in the "delivery" group
```

**Example: delivery user updates status to “Delivered”**
- **who**: delivery (for their assigned orders) or admin
  
```bash
# "delivered" has id = 3
DELIVERER_ACCESS="<deliverer access token>"

curl -X PATCH http://127.0.0.1:8000/api/store/orders/101 \
  -H "Authorization: Bearer $DELIVERER_ACCESS" \
  -H "Content-Type: application/json" \
  -d '{ "status": 3 }'
```

**Example: customer requests a cancellation or refund**
- **who**: customer (only for their order)
- **rules**:
  - `intent: "cancellation"` allowed when status is `pending` or `failed`
  - `intent: "refund"` allowed when status is `delivered`
- **effect**: status changes to under-review and a history entry is logged.

```bash
# Request cancellation
CUSTOMER_ACCESS="<customer access token>"

curl -X PATCH http://127.0.0.1:8000/api/store/orders/102 \
  -H "Authorization: Bearer $CUSTOMER_ACCESS" \
  -H "Content-Type: application/json" \
  -d '{ "intent": "cancellation" }'
```

```bash
# Request refund
curl -X PATCH http://127.0.0.1:8000/api/store/orders/103 \
  -H "Authorization: Bearer $CUSTOMER_ACCESS" \
  -H "Content-Type: application/json" \
  -d '{ "intent": "refund" }'
```

**Example: customer updates delivery address (only in `pending` or `failed`)**

```bash
curl -X PATCH http://127.0.0.1:8000/api/store/orders/104 \
  -H "Authorization: Bearer $CUSTOMER_ACCESS" \
  -H "Content-Type: application/json" \
  -d '{ "delivery_address": 13 }'
```

---

### Order Items (by order)

**Endpoints**

- `GET /orders/<order_id>/items` — list items for a given order

**Permissions**

- **Delivery** is **denied** access to order contents.
- **Admin/Manager** see items (any order).
- **Customers** see items **only for their own orders**.

---

### Order History (by order)

**Endpoints**

- `GET /orders/<order_id>/history` — list chronological status changes and actions

**Permissions**

- Same as Order Items (above).

**Notes**

- Each history row includes `status_display`, `timestamp` (localized), `performed_by`, and `action`.


---

## Filtering & search summary

| Resource | Search | Ordering | Filters (selected) |
|---|---|---|---|
| **Books** | `title`, `author`, `genre__title`, `publisher` | `author`, `title`, `edition`, `price`, `discount` | `genre`, `book_format`, `language`, `is_new`, `stock`, `discount_gte/lte`, `first_publication_year_gte/lte`, `price_min/max`, `rating_min/max`, `is_bc` |
| **Reviews** | `user__username` | `rating`, `created_at`, `updated_at` | `rating_gte/lte`, `created_at_gte/lte`, `updated_at_gte/lte`, `user` |
| **Cart** | `user__username`, `book__title`, `book__author` | `unit_price`, `price`, `quantity` | `quantity_gte/lte`, `unit_price_gte/lte`, `price_gte/lte`, `user` |
| **Orders** | `user__username` | `total`, `when_placed`, `status` | `total_gte/lte`, `when_placed_gte/lte`, `when_last_update_gte/lte`, `user`, `deliverer`, `status` |
| **Order History** | `order__user__username`, `performed_by__username`, `action` | `timestamp` | `timestamp_gte/lte`, `order`, `action` |

> Filtering/search/order backends are configured globally; numeric/date range helpers are implemented via reusable base filter sets.

---

## Validation highlights

- **Books**
  - `isbn` validated/normalized (ISBN-10/13), uniqueness enforced
  - `first_publication_year`: must be > 0; AD years cannot be in the future
  - Strict HTML sanitization on char fields; HTML allowed (cleaned) in `blurb`
- **Cart**
  - Prevents adding `out-of-stock` or `discontinued`
  - `PATCH` supports **only** `quantity`
- **Orders**
  - Enforces allowed **field edits per role**
  - Enforces **status transition** matrix by role
  - Records `OrderHistory` with messages for key actions (e.g., customer intent)

---

## Error shapes

- **Validation error** (e.g., illegal status transition, duplicate address):

```json
{
  "detail": "Cannot delete this book because it is referenced by one or more orders."
}
```

or field-mapped errors:

```json
{
  "status": [
    "You cannot update an order status from Pending to Delivered"
  ]
}
```

- **Permission denied**:

```json
{ "detail": "You do not have permission to perform this action." }
```

- **Not found** (including nested review/book mismatch):

```json
{ "detail": "Not found." }
```

---

## FAQ / troubleshooting

- **“Why does the demo run without setting a secret?”**  
  `base.py` includes a **demo-only** fallback key so you can clone & run. Use the **prod-like** settings to enforce a strong key.

- **“How do I run on Windows?”**  
  See the Windows quickstart above; use `$env:NAME = "value"`, `py -m venv .venv`, and PowerShell mappings.

- **“What are the default throttle limits?”**  
  See the Throttling section — limits and scopes are defined in the settings.

---

## License

This project is licensed under the [MIT License](LICENSE).

---

### Notes for reviewers

- The code intentionally demonstrates **separation of concerns**: serializers validate and shape responses; a dedicated **service object** (order updater) encapsulates business rules; permissions and throttles are simple and composable.
- The API returns **minimalist list payloads** (smart list/detail representation) and drops `url` in detail views to keep responses lean and legible.