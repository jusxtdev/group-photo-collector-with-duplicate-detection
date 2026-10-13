# gpc-with-dd frontend

Minimal vanilla HTML/CSS/JS frontend for testing and MVP purposes.
No build step. All backend calls go through `js/api.js`.

## Run

1. Start the backend (from `backend/`):

   ```
   uv run uvicorn src.main:app --reload
   ```

2. Serve this directory over HTTP (ES modules require a real server):

   ```
   python3 -m http.server 5173
   ```

3. Open http://localhost:5173

The backend must allow this origin. CORS origins are configured via
`cors_origins` in `backend/src/core/config.py` (defaults to
`http://localhost:5173` and `http://127.0.0.1:5173`).

## API base URL

Set in `js/config.js` (`API_BASE`, defaults to `http://127.0.0.1:8000`).

## Structure

```
index.html    login / signup
albums.html   list, create, join albums
album.html    album detail (?id=<album_id>)
css/styles.css
js/config.js  API_BASE + storage keys
js/api.js     fetch wrapper, token storage, error handling
js/auth.js    login/signup page logic
js/albums.js  albums page logic
js/album.js   album detail page logic
```

## Notes

- Auth token stored in `localStorage` under `gpc_token`.
- Photo upload and gallery listing are implemented: `POST
  /photo/albums/{id}/photos/batch` for uploads and `GET
  /photo/albums/{id}/photos` for the gallery (pre-signed URLs).
- The token is kept in `localStorage` for simplicity; revisit before production.
