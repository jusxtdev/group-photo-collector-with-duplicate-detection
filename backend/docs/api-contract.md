# Backend API Contract

Source of truth for the externally observable behavior of the backend API. This
document reflects the implementation in `src/` as of the current commit.

## 1. Overview

- **Purpose:** Backend for a shared photo-album application. It provides user
  registration and login (JWT bearer auth), album creation/joining, album
  membership management (roles, removal, and voluntary leaving), album
  listing/detail retrieval, album title editing, and album deletion.
- **Framework:** FastAPI (see `src/main.py`), served by Uvicorn.
- **Base URL / base path:** There is no configured base path or route prefix;
  every route is mounted at the application root. The backend code does not
  define host or port. The bundled frontend (`frontend/js/config.js`) targets
  `http://127.0.0.1:8000`, which is the default FastAPI/Uvicorn local address.
  No other base URL is established by the backend.
- **Versioning:** None. Routes are unversioned.
- **Authentication:** JWT bearer tokens (`Authorization: Bearer <token>`),
  issued by `POST /login` or `POST /login/token`.
- **Interactive docs:** FastAPI exposes the auto-generated Swagger UI at `/docs`
  and the OpenAPI schema at `/openapi.json` (framework behavior).
- **CORS:** Configured via the `cors_origins` setting; defaults to
  `http://localhost:5173` and `http://127.0.0.1:5173`. Credentials, all methods,
  and all headers are allowed.

## 2. Conventions

- **Request content types:**
  - `application/json` for JSON bodies (`/signup`, `/login`, `/album`,
    `/albums/join`, the album update endpoint, and the role update endpoint).
  - `application/x-www-form-urlencoded` for `POST /login/token` (OAuth2 password
    form).
- **Success response envelope:** All JSON endpoints except `POST /login/token`
  return the envelope:

  ```json
  { "status": true, "msg": "<message>", "data": <payload or null> }
  ```

  The `data` field is always present and defaults to `null` when there is no
  payload.

- **Error response envelope:** Application and HTTP errors raised via
  `HTTPException` are rendered by a custom handler (`src/main.py:22`) as:

  ```json
  { "status": false, "msg": "<detail>", "data": null }
  ```

- **Validation error format:** Request validation failures return HTTP 422 with:

  ```json
  {
    "status": false,
    "msg": "Validation error",
    "data": [
      {
        "type": "string_too_short",
        "loc": ["body", "title"],
        "msg": "String should have at least 1 character",
        "input": "",
        "ctx": { "min_length": 1 },
        "url": "https://errors.pydantic.dev/2.14/v/string_too_short"
      }
    ]
  }
  ```

  `loc` begins with the source (`body`, `path`, or `query`). `data` is the raw
  list from Pydantic's `errors()`, encoded with `jsonable_encoder`.

- **Authentication header:** `Authorization: Bearer <JWT>`. Missing or invalid
  tokens produce HTTP 401. See section 4 for details, including the fact that
  the `WWW-Authenticate` header is not preserved by the custom error handler.

- **Datetime format:** Timestamps are returned in ISO 8601 format (the API
  returns timezone-aware datetimes populated by the database).

- **Token type:** Always `"bearer"` (hard-coded in `Token`).

## 3. Endpoint Reference

### 3.1 `GET /health`

- **Purpose:** Liveness check.
- **Auth:** None.
- **Parameters:** None.
- **Success:** `200 OK`

  ```json
  { "status": true, "msg": "Service is healthy", "data": null }
  ```

- **Errors:** None defined.

---

### 3.2 `POST /signup`

- **Purpose:** Register a new user.
- **Auth:** None.
- **Body (`application/json`):**

  | Field | Type | Required | Constraints |
  |-------|------|----------|-------------|
  | `name` | string | yes | length 1–255 |
  | `email` | string | yes | length 1–255; not validated as an email format; must be unique |
  | `password` | string | yes | length 8–128 |

- **Success:** `201 Created`

  ```json
  {
    "status": true,
    "msg": "User created",
    "data": {
      "id": 1,
      "name": "Ada Lovelace",
      "email": "ada@example.com",
      "created_at": "2026-10-10T07:00:00Z",
      "updated_at": "2026-10-10T07:00:00Z"
    }
  }
  ```

- **Errors:**
  - `409 Conflict` — email already registered. `msg` = `A user with email
    '<email>' already exists` (Python `repr` quoting) .
  - `422 Unprocessable Entity` — schema/constraint violation.
- **Side effects:** Creates a `user` row. Password is stored only as an Argon2
  hash (`password_hash`); it is never returned.

---

### 3.3 `POST /login`

- **Purpose:** Authenticate with JSON and obtain an access token.
- **Auth:** None.
- **Body (`application/json`):**

  | Field | Type | Required | Constraints |
  |-------|------|----------|-------------|
  | `email` | string | yes | length 1–255 |
  | `password` | string | yes | length 1–128 |

- **Success:** `200 OK`

  ```json
  {
    "status": true,
    "msg": "Login successful",
    "data": { "access_token": "<jwt>", "token_type": "bearer" }
  }
  ```

- **Errors:**
  - `401 Unauthorized` — `msg` = `Invalid email or password` (returned for both
    unknown email and wrong password; response is the standard error envelope).
  - `422 Unprocessable Entity` — schema/constraint violation.

---

### 3.4 `POST /login/token`

- **Purpose:** OAuth2 password-flow token endpoint. This is the `tokenUrl`
  referenced by the bearer authentication scheme (`src/core/deps.py:9`).
- **Auth:** None.
- **Request:** `application/x-www-form-urlencoded` with fields:
  - `username` (required) — treated as the user's email.
  - `password` (required).
  - `grant_type`, `scope`, `client_id`, `client_secret` are accepted by
    FastAPI's form model but are not used by the handler.
- **Success:** `200 OK`. **This endpoint does NOT use the `ApiResponse`
  envelope**; it returns the token object directly:

  ```json
  { "access_token": "<jwt>", "token_type": "bearer" }
  ```

- **Errors:**
  - `401 Unauthorized` — `msg` = `Invalid email or password`. The handler sets
    a `WWW-Authenticate: Bearer` header, but the custom exception handler does
    not preserve it (see section 4 and section 7).
  - `422 Unprocessable Entity` — missing required form fields.

---

### 3.5 `POST /album`

- **Purpose:** Create an album; the creator becomes its `owner` member.
- **Auth:** Required (bearer token).
- **Body (`application/json`):**

  | Field | Type | Required | Constraints |
  |-------|------|----------|-------------|
  | `title` | string | yes | length 1–255 |

- **Success:** `201 Created`

  ```json
  {
    "status": true,
    "msg": "Album created",
    "data": {
      "id": 10,
      "title": "Summer Trip",
      "created_by": 1,
      "created_at": "2026-10-10T07:00:00Z",
      "updated_at": "2026-10-10T07:00:00Z",
      "join_code": "ABCD2345"
    }
  }
  ```

- **Notes:** `join_code` is a plaintext 8-character code revealed only here. The
  database stores only its SHA-256 hash (`album.join_code_hash`, unique). The
  code alphabet is `ABCDEFGHJKMNPQRSTUVWXYZ23456789` (no `I`, `L`, `O`, `0`, `1`).
- **Errors:**
  - `401 Unauthorized` — missing/invalid token.
  - `422 Unprocessable Entity` — schema/constraint violation.
  - `500 Internal Server Error` — `msg` = `Could not generate a unique join code
    for the album`, after 5 failed attempts to generate a unique code.
- **Side effects:** Creates an `album` row and an `album_members` row linking the
  creator with role `owner`.

---

### 3.6 `GET /album`

- **Purpose:** List the albums the current user is a member of.
- **Auth:** Required (bearer token).
- **Parameters:** None.
- **Success:** `200 OK`

  ```json
  {
    "status": true,
    "msg": "Albums retrieved",
    "data": [
      {
        "id": 10,
        "title": "Summer Trip",
        "created_by": 1,
        "created_at": "2026-10-10T07:00:00Z",
        "updated_at": "2026-10-10T07:00:00Z",
        "role": "owner"
      }
    ]
  }
  ```

- **Notes:**
  - `role` is the current user's role in each album: `"owner"` or `"member"`.
  - Results are ordered by `created_at` descending, then `id` descending.
  - Only albums where the user has an `album_members` row are included.
  - No pagination.
- **Errors:** `401 Unauthorized`.

---

### 3.7 `GET /album/{album_id}`

- **Purpose:** Retrieve album detail, including the caller's role and counts.
- **Auth:** Required (bearer token); caller must be a member of the album.
- **Path parameters:**
  - `album_id` (integer) — album ID.
- **Success:** `200 OK`

  ```json
  {
    "status": true,
    "msg": "Album retrieved",
    "data": {
      "id": 10,
      "title": "Summer Trip",
      "created_by": 1,
      "created_at": "2026-10-10T07:00:00Z",
      "updated_at": "2026-10-10T07:00:00Z",
      "role": "owner",
      "photo_count": 0,
      "member_count": 2,
      "owner_count": 1
    }
  }
  ```

- **Notes:** `photo_count` counts `photos` rows for the album; `member_count` and
  `owner_count` count `album_members` rows. `role` is the caller's role.
- **Errors:**
  - `401 Unauthorized`.
  - `404 Not Found` — `msg` = `Album not found`. Returned both when the album
    does not exist and when the caller is not a member (non-membership is not
    distinguished from non-existence; no 403 is returned here).
  - `422 Unprocessable Entity` — `album_id` not an integer.

---

### 3.8 `POST /albums/join`

- **Purpose:** Join an album using its join code; the caller is added as a
  `member`.
- **Auth:** Required (bearer token).
- **Body (`application/json`):**

  | Field | Type | Required | Constraints |
  |-------|------|----------|-------------|
  | `join_code` | string | yes | length 1–64; surrounding whitespace is trimmed before lookup |

- **Success:** `201 Created`

  ```json
  {
    "status": true,
    "msg": "Joined album",
    "data": {
      "id": 10,
      "title": "Summer Trip",
      "created_by": 1,
      "created_at": "2026-10-10T07:00:00Z",
      "updated_at": "2026-10-10T07:00:00Z",
      "role": "member"
    }
  }
  ```

- **Errors:**
  - `401 Unauthorized`.
  - `404 Not Found` — `msg` = `Invalid join code` (no album matches the hash of
    the provided code).
  - `409 Conflict` — `msg` = `Already a member of this album`.
  - `422 Unprocessable Entity` — schema/constraint violation.
- **Side effects:** Adds an `album_members` row with role `member`.

---

### 3.9 `GET /albums/{album_id}/members`

- **Purpose:** List the members of an album.
- **Auth:** Required (bearer token); caller must be a member of the album.
- **Path parameters:**
  - `album_id` (integer) — album ID.
- **Success:** `200 OK`

  ```json
  {
    "status": true,
    "msg": "Members retrieved",
    "data": [
      {
        "user_id": 1,
        "name": "Ada Lovelace",
        "role": "owner",
        "joined_at": "2026-10-10T07:00:00Z"
      }
    ]
  }
  ```

- **Notes:**
  - `joined_at` is the membership's `created_at`.
  - Ordered by membership `created_at` ascending, then `user.id` ascending.
  - No pagination.
- **Errors:**
  - `401 Unauthorized`.
  - `404 Not Found` — `msg` = `Album not found`. Returned when the album does not
    exist or the caller is not a member.
  - `422 Unprocessable Entity` — `album_id` not an integer.

---

### 3.10 `PATCH /albums/{album_id}/members/{user_id}/role`

- **Purpose:** Promote a member to `owner` or demote an `owner` to `member`.
- **Auth:** Required (bearer token). Authorization depends on the direction of
  the change (see below).
- **Path parameters:**
  - `album_id` (integer) — album ID.
  - `user_id` (integer) — ID of the member whose role is changing.
- **Body (`application/json`):**

  | Field | Type | Required | Constraints |
  |-------|------|----------|-------------|
  | `role` | string enum | yes | one of `"owner"` or `"member"` |

- **Authorization rules (from `src/services/album.py`, `update_member_role`):**
  - Caller must be a member of the album (otherwise `404`).
  - **Promotion to `owner`:** caller must already be an `owner`.
  - **Demotion to `member`:** caller must be the album's creator
    (`album.created_by`), i.e. the "main owner".
- **Success:** `200 OK`

  ```json
  {
    "status": true,
    "msg": "Member promoted to owner",
    "data": { "user_id": 2, "name": "Grace Hopper", "role": "owner", "joined_at": "2026-10-10T07:05:00Z" }
  }
  ```

  Demotion returns `msg` = `Owner demoted to member`.

- **Errors:**

  | Status | `msg` | Condition |
  |--------|-------|-----------|
  | `400` | `The album owner cannot be demoted` | Demoting the album's creator |
  | `401` | `Could not validate credentials` | Invalid/expired token or unknown user |
  | `403` | `Only album owners can change member roles` | Non-owner tries to promote someone to owner |
  | `403` | `Only the album owner can demote members` | Non-creator tries to demote an owner |
  | `404` | `Album not found` | Caller is not a member (or album missing) |
  | `404` | `User is not a member of this album` | Target user has no membership |
  | `409` | `User is already an owner of this album` | Promoting an existing owner |
  | `409` | `User is not an owner of this album` | Demoting a non-owner |
  | `422` | `Validation error` | `role` not `owner`/`member`, or path param not integer |

- **Side effects:** Updates the target membership's `role`. The album's creator
  (`created_by`) is immutable and can never be demoted; multiple owners are
  allowed.

---

### 3.11 `DELETE /albums/{album_id}/members/{user_id}`

- **Purpose:** Remove another user from an album. Also removes the caller's own
  membership when `user_id` equals the caller's ID (equivalent to leaving; see
  section 3.12).
- **Auth:** Required (bearer token); caller must be a member of the album.
- **Path parameters:**
  - `album_id` (integer) — album ID.
  - `user_id` (integer) — ID of the member to remove.
- **Success:** `200 OK`

  ```json
  {
    "status": true,
    "msg": "Member removed",
    "data": { "user_id": 2, "name": "Grace Hopper", "role": "member", "joined_at": "2026-10-10T07:05:00Z" }
  }
  ```

  The `data` object describes the membership that was removed (same shape as
  section 3.9 entries).

- **Authorization rules (evaluated in this order, from
  `src/services/album.py`, `remove_member`):**
  1. Caller must have a membership in the album (otherwise `404 Album not
     found`).
  2. Target must have a membership in the album (otherwise `404 User is not a
     member of this album`).
  3. If the target is **not** the caller:
     - Caller must be an `owner` (otherwise `403 Only album owners can remove
       members`).
     - If the target is an `owner`, the caller must be the album creator
       (`album.created_by`), otherwise `403 Only the album creator can remove
       other owners`.
  4. If the target is the album creator → `400 The album creator cannot be
     removed`. This is checked last, so the only way it triggers is the creator
     removing their own membership (any other caller attempting to remove the
     creator is rejected at step 3, since the creator is an owner).
- **Errors:**

  | Status | `msg` | Condition |
  |--------|-------|-----------|
  | `400` | `The album creator cannot be removed` | Target is the album creator |
  | `401` | `Not authenticated` | Missing bearer token |
  | `401` | `Could not validate credentials` | Invalid/expired token or unknown user |
  | `403` | `Only album owners can remove members` | Non-owner removes another user |
  | `403` | `Only the album creator can remove other owners` | Non-creator owner removes an owner |
  | `404` | `Album not found` | Caller is not a member, or album missing |
  | `404` | `User is not a member of this album` | Target has no membership |
  | `422` | `Validation error` | Path param not an integer |

- **Side effects:** Deletes the target `album_members` row. The removed user
  loses all access to the album. `album.created_by` is never changed, and the
  creator can never be removed (see sections 3.11/3.12 and section 6). Photos
  previously uploaded by the removed user are not affected (membership deletion
  does not cascade to `photos`).

---

### 3.12 `DELETE /albums/{album_id}/members/me`

- **Purpose:** Leave an album voluntarily.
- **Auth:** Required (bearer token); caller must be a member of the album.
- **Path parameters:**
  - `album_id` (integer) — album ID.
- **Success:** `200 OK`

  ```json
  {
    "status": true,
    "msg": "Left album",
    "data": { "user_id": 3, "name": "Alan Turing", "role": "member", "joined_at": "2026-10-10T07:10:00Z" }
  }
  ```

- **Notes:**
  - Equivalent to `DELETE /albums/{album_id}/members/{caller_id}`.
  - The `/members/me` path is matched before `/members/{user_id}`.
  - Any member can leave, including a **promoted** owner. The original creator
    cannot leave (see errors).
- **Errors:**
  - `401 Unauthorized` — missing/invalid token.
  - `404 Not Found` — `msg` = `Album not found` (caller has no membership in the
    album).
  - `400 Bad Request` — `msg` = `The album creator cannot be removed` (the
    creator cannot leave their own album).
  - `422 Unprocessable Entity` — `album_id` not an integer.
- **Side effects:** Deletes the caller's `album_members` row. If the caller was
  an owner and other owners remain, the album continues normally; the last owner
  can never leave because the creator is permanent.

---

### 3.13 `PATCH /albums/{album_id}`

- **Purpose:** Update an album's title. Only owners may edit the album.
- **Auth:** Required (bearer token); caller must be a member of the album and
  hold the `owner` role.
- **Path parameters:**
  - `album_id` (integer) — album ID.
- **Request body:** `application/json`

  ```json
  { "title": "Summer 2026" }
  ```

  - `title` (string, required) — 1–255 characters. Only `title` is accepted; the
    album's `created_by` and timestamps cannot be set by clients.

- **Success:** `200 OK`

  ```json
  {
    "status": true,
    "msg": "Album updated",
    "data": {
      "id": 5,
      "title": "Summer 2026",
      "created_by": 1,
      "created_at": "2026-10-10T07:00:00Z",
      "updated_at": "2026-10-10T07:30:00Z"
    }
  }
  ```

  `data` has the same shape as section 3.4 (`AlbumRead`). `updated_at` is
  refreshed automatically by the database (`onupdate`).

- **Authorization rules (from `src/services/album.py`, `update_album_title`):**
  1. Caller must have a membership in the album (otherwise `404 Album not
     found` — existence is hidden from non-members).
  2. Caller must be an `owner` (otherwise `403 Only album owners can edit the
     album`).
- **Errors:**

  | Status | `msg` | Condition |
  |--------|-------|-----------|
  | `401` | `Not authenticated` | Missing bearer token |
  | `401` | `Could not validate credentials` | Invalid/expired token or unknown user |
  | `403` | `Only album owners can edit the album` | Caller is a member but not an owner |
  | `404` | `Album not found` | Caller is not a member, or album missing |
  | `422` | `Validation error` | `title` missing/empty/>255 chars/wrong type, or `album_id` not an integer |

- **Side effects:** Updates the album's `title` (and its `updated_at`). No other
  fields are modified. Multiple owners may all edit the title.

---

### 3.14 `DELETE /albums/{album_id}`

- **Purpose:** Permanently delete an album and its dependent records. Only the
  album's original creator may delete the album.
- **Auth:** Required (bearer token); caller must be a member of the album and be
  the album's `created_by` user.
- **Path parameters:**
  - `album_id` (integer) — album ID.
- **Success:** `200 OK`

  ```json
  {
    "status": true,
    "msg": "Album deleted",
    "data": {
      "id": 5,
      "title": "Summer 2026",
      "created_by": 1,
      "created_at": "2026-10-10T07:00:00Z",
      "updated_at": "2026-10-10T07:30:00Z"
    }
  }
  ```

  `data` is a snapshot of the deleted album (`AlbumRead` shape) captured before
  deletion.

- **Authorization rules (from `src/services/album.py`, `delete_album`):**
  1. Caller must have a membership in the album (otherwise `404 Album not
     found` — existence is hidden from non-members).
  2. Caller must be the album creator (`album.created_by`). Any other caller,
     including a promoted owner, gets `403 Only the album creator can delete the
     album`.
- **Errors:**

  | Status | `msg` | Condition |
  |--------|-------|-----------|
  | `401` | `Not authenticated` | Missing bearer token |
  | `401` | `Could not validate credentials` | Invalid/expired token or unknown user |
  | `403` | `Only the album creator can delete the album` | Caller is a member/owner but not the creator |
  | `404` | `Album not found` | Caller is not a member, or album missing |
  | `422` | `Validation error` | `album_id` not an integer |

- **Side effects:** Deletes the `album` row and cascades (ORM-level `all,
  delete-orphan`) to all of its `album_members` and `photos` rows. Deleting an
  album does **not** delete the creator or member user accounts, and does not
  delete any user's other albums.
  - **Object storage (R2):** No object-storage integration is implemented yet, so
    no R2 objects are deleted. The `photos` rows are removed, but any
    corresponding external objects (were an upload flow to exist) are left in
    place. See section 7.

## 4. Authentication and Authorization

- **Token issuance:** `POST /login` (JSON) and `POST /login/token` (form). Both
  return a JWT whose `sub` claim is the user ID as a string, with an `exp`
  claim set to now + `access_token_expire_minutes` (default `60`, configurable
  via settings). Algorithm defaults to `HS256`.
- **Token usage:** Protected endpoints depend on `get_current_user`
  (`src/core/deps.py:12`), which reads the bearer token, decodes it, and loads
  the user. If decoding fails, `sub` is missing/not an int, or the user does not
  exist, it raises `401` with `msg` = `Could not validate credentials`.
- **Missing token:** FastAPI's `OAuth2PasswordBearer(auto_error=True)` raises a
  `401` with detail `Not authenticated` while resolving the `oauth2_scheme`
  dependency, before `get_current_user` body executes.
- **`WWW-Authenticate` header:** `get_current_user` and `login_token` set
  `WWW-Authenticate: Bearer`, but the custom `HTTPException` handler
  (`src/main.py:22`) rebuilds the response from `msg`/`data` only and discards
  all headers. Consequently, `401` responses do not include
  `WWW-Authenticate` in practice.
- **Protected endpoints:** `POST /album`, `GET /album`, `GET /album/{album_id}`,
  `POST /albums/join`, `GET /albums/{album_id}/members`,
  `PATCH /albums/{album_id}/members/{user_id}/role`,
  `DELETE /albums/{album_id}/members/{user_id}`,
  `DELETE /albums/{album_id}/members/me`,
  `PATCH /albums/{album_id}`, `DELETE /albums/{album_id}`.
- **Role / ownership checks:** Enforced at the service layer (sections 3.10–3.14),
  not via middleware or dependency-level role guards.
- **Non-member access:** Album-scoped endpoints hide existence from non-members
  by returning `404` rather than `403` (applies to album detail, title update,
  album deletion, members list, member removal, leave, and the role endpoint,
  where a non-member also gets `404 Album not found` before any role logic).

## 5. Error Reference

All application/HTTP errors (except validation) share the shape
`{"status": false, "msg": <string>, "data": null}`. Validation errors use
`data` as a list (section 2).

| Status | `msg` | Where |
|--------|-------|-------|
| `400` | `The album owner cannot be demoted` | Role update |
| `400` | `The album creator cannot be removed` | Member removal / leave |
| `401` | `Not authenticated` | Missing bearer token (framework) |
| `401` | `Could not validate credentials` | Invalid/expired token or unknown user |
| `401` | `Invalid email or password` | Login endpoints |
| `403` | `Only album owners can change member roles` | Role update |
| `403` | `Only the album owner can demote members` | Role update |
| `403` | `Only album owners can remove members` | Member removal |
| `403` | `Only the album creator can remove other owners` | Member removal |
| `403` | `Only album owners can edit the album` | Album update |
| `403` | `Only the album creator can delete the album` | Album deletion |
| `404` | `Album not found` | Album detail, album update, album deletion, members list, role update, member removal, leave |
| `404` | `Invalid join code` | Join album |
| `404` | `User is not a member of this album` | Role update, member removal |
| `409` | `A user with email '<email>' already exists` | Signup |
| `409` | `Already a member of this album` | Join album |
| `409` | `User is already an owner of this album` | Role update |
| `409` | `User is not an owner of this album` | Role update |
| `500` | `Could not generate a unique join code for the album` | Create album |
| `422` | `Validation error` | All endpoints with bodies/params |

Note: unexpected server exceptions are not handled by a catch-all handler and
would return FastAPI/Starlette's default `500 Internal Server Error` body (not
the `ApiResponse` envelope).

## 6. Important Behavioral Rules

- **Unique email:** `user.email` is unique. No case normalization is applied in
  the application, so uniqueness follows the database's default string
  comparison.
- **Unique join code:** `album.join_code_hash` is unique. Plaintext join codes
  are never returned after album creation and only hashes are stored.
- **Join code lookup:** Whitespace around the submitted `join_code` is trimmed
  before hashing.
- **Album membership:** A user can hold at most one membership row per album
  (composite primary key `user_id`, `album_id`). The creator is always an
  `owner`. A user creating an album is automatically an owner.
- **Multiple owners:** Promotion allows more than one owner per album.
- **Immutable/ permanent creator:** The album's `created_by` user can never be
  demoted (role update), removed, or leave. Because the creator is always an
  owner, an album always has at least one owner; consequently the last owner can
  never be removed or demoted.
- **Member removal and leaving:** An owner may remove a member; only the album
  creator can remove another owner; any member (including a promoted owner) may
  remove themselves (leave) as long as they are not the creator.
- **Album editing:** Only owners may change an album's `title` (`PATCH
  /albums/{album_id}`, section 3.13). Members who are not owners get `403`; the
  album's `created_by` and timestamps are not client-editable.
- **Album deletion:** Only the album's original creator may delete an album
  (`DELETE /albums/{album_id}`, section 3.14). Other members, including promoted
  owners, get `403`. Deletion cascades to the album's `photos` and
  `album_members` rows (ORM-level `all, delete-orphan`) and does not affect user
  accounts or other albums. No external object storage (R2) integration exists
  yet, so no R2 objects are deleted.
- **Ordering:** Album list is newest-first (`created_at` desc, `id` desc); member
  list is oldest-first (`created_at` asc, `user.id` asc).
- **No pagination, filtering, or sorting parameters** are implemented on any
  endpoint.
- **Photos:** A `photos` table and `Photo` model exist (`id`, `album_id`,
  `uploaded_by`, `sha256`, `phash`, `object_key`, timestamps), and `photo_count`
  is surfaced in album detail, but **no photo endpoints are implemented**.
  `object_key` stores the object-storage key and is `NOT NULL`; nothing writes it
  yet (see section 7).

## 7. Uncertainties and Gaps

- **No automated tests exist** in the repository (no `test_*` files, no test
  configuration). All statements here are derived from source inspection and
  manual HTTP verification.
- **Object storage (R2) not implemented:** There is no Cloudflare R2 / S3
  client, no storage configuration (the `.env` file defines only `DATABASE_URL`
  and `JWT_SECRET`), and no upload flow, despite `boto3` being a declared
  dependency. The `Photo` model has an `object_key` column (`String(1024)`,
  `NOT NULL`) intended to hold the object-storage key, in addition to `sha256`
  and `phash`, but no code populates it and no R2 key scheme is defined.
  Consequently, album deletion removes `photos` rows but does **not** delete any
  R2 objects. This gap will matter once photo upload/storage is implemented.
- **Base URL/port:** Not defined in backend code. `http://127.0.0.1:8000` is
  taken from the frontend configuration and from Uvicorn's default; it is not a
  backend-guaranteed contract.
- **Timestamps in examples** are illustrative placeholders; actual values are
  database-generated.
- **Validation error `data` payload:** The envelope shape and the inclusion of
  the `ctx` and `url` fields were verified by invoking the exception handler
  directly (Pydantic 2.14). `jsonable_encoder` is applied to the error list; the
  exact encoded form for error types whose `ctx` contains non-JSON-native values
  was not exhaustively verified.
- **Error handlers:** `http_exception_handler` and `validation_exception_handler`
  were invoked directly and confirmed to produce the shapes documented above;
  they were not exercised through a running HTTP server (the `httpx` dependency
  required by FastAPI's `TestClient` is not installed).
- **Dropped `WWW-Authenticate` header:** Confirmed by direct invocation of the
  custom handler (it constructs `JSONResponse` with no headers, so the header set
  by `get_current_user`/`login_token` is lost).
- **`POST /login/token` envelope inconsistency:** Unlike every other JSON
  endpoint, it returns the bare `Token` object rather than `ApiResponse`. This is
  intentional for OAuth2 compatibility but is a notable divergence.
- **Generated OpenAPI vs. actual errors:** The auto-generated schema at
  `/openapi.json` documents `422` responses as `HTTPValidationError`, but the
  runtime custom handler instead returns the
  `{"status": false, "msg": "Validation error", "data": [...]}` envelope. The
  runtime behavior is documented above; the generated schema is inaccurate for
  error bodies.
- **CORS behavior under real requests** (including credentialed requests and
  preflight) was not executed; only the middleware configuration was inspected.
