import { request, requireAuth, clearToken } from "./api.js";

function showMessage(text, kind = "error") {
  const el = document.getElementById("message");
  el.textContent = text;
  el.className = `message ${kind}`;
  el.hidden = !text;
}

function statCard(label, value) {
  const card = document.createElement("div");
  card.className = "stat";
  const valueEl = document.createElement("span");
  valueEl.className = "stat-value";
  valueEl.textContent = value;
  const labelEl = document.createElement("span");
  labelEl.className = "stat-label";
  labelEl.textContent = label;
  card.append(valueEl, labelEl);
  return card;
}

function renderAlbum(album) {
  document.getElementById("album-title").textContent = album.title;

  const role = document.getElementById("album-role");
  role.textContent = album.role;
  role.className = `badge ${album.role}`;

  const stats = document.getElementById("stats");
  stats.innerHTML = "";
  stats.append(
    statCard("Photos", album.photo_count),
    statCard("Members", album.member_count),
    statCard("Owners", album.owner_count),
  );
}

async function loadAlbum(id) {
  try {
    const album = await request(`/album/${id}`);
    renderAlbum(album);
  } catch (err) {
    showMessage(err.message);
  }
}

function init() {
  if (!requireAuth()) return;

  document.getElementById("logout").addEventListener("click", () => {
    clearToken();
    window.location.href = "index.html";
  });

  const id = new URLSearchParams(window.location.search).get("id");
  if (!id) {
    showMessage("No album id provided");
    return;
  }
  loadAlbum(id);
}

init();
