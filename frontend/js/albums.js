import { request, clearToken, requireAuth } from "./api.js";

const state = { albums: [] };

function showMessage(text, kind = "error") {
  const el = document.getElementById("message");
  el.textContent = text;
  el.className = `message ${kind}`;
  el.hidden = !text;
}

function renderAlbums() {
  const container = document.getElementById("album-list");
  container.innerHTML = "";

  if (state.albums.length === 0) {
    const empty = document.createElement("p");
    empty.className = "muted";
    empty.textContent = "No albums yet. Create one or join with a code.";
    container.appendChild(empty);
    return;
  }

  for (const album of state.albums) {
    const card = document.createElement("a");
    card.className = "album-card";
    card.href = `album.html?id=${album.id}`;

    const title = document.createElement("h3");
    title.textContent = album.title;

    const meta = document.createElement("div");
    meta.className = "meta";

    const role = document.createElement("span");
    role.className = `badge ${album.role}`;
    role.textContent = album.role;

    meta.appendChild(role);
    card.append(title, meta);
    container.appendChild(card);
  }
}

async function loadAlbums() {
  try {
    state.albums = await request("/album");
    renderAlbums();
  } catch (err) {
    showMessage(err.message);
  }
}

async function handleCreate(event) {
  event.preventDefault();
  const input = document.getElementById("create-title");
  const title = input.value.trim();
  if (!title) return;

  try {
    const album = await request("/album", { method: "POST", body: { title } });
    input.value = "";
    showJoinCode(album.join_code);
    await loadAlbums();
  } catch (err) {
    showMessage(err.message);
  }
}

async function handleJoin(event) {
  event.preventDefault();
  const input = document.getElementById("join-code");
  const join_code = input.value.trim();
  if (!join_code) return;

  try {
    await request("/albums/join", { method: "POST", body: { join_code } });
    input.value = "";
    showMessage("Joined album", "success");
    await loadAlbums();
  } catch (err) {
    showMessage(err.message);
  }
}

function showJoinCode(code) {
  const box = document.getElementById("join-code-result");
  const value = document.getElementById("join-code-value");
  value.textContent = code;
  box.hidden = false;
}

function init() {
  if (!requireAuth()) return;

  document.getElementById("logout").addEventListener("click", () => {
    clearToken();
    window.location.href = "index.html";
  });

  document.getElementById("create-form").addEventListener("submit", handleCreate);
  document.getElementById("join-form").addEventListener("submit", handleJoin);

  document.getElementById("copy-code").addEventListener("click", async () => {
    const code = document.getElementById("join-code-value").textContent;
    try {
      await navigator.clipboard.writeText(code);
      showMessage("Join code copied", "success");
    } catch (err) {
      showMessage("Copy failed - select the code manually");
    }
  });

  loadAlbums();
}

init();
