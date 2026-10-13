import { request, requireAuth, clearToken, getCurrentUserId } from "./api.js?v=3";

let albumId = null;
let currentRole = null;
let albumCreatedBy = null;

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
  currentRole = album.role;
  albumCreatedBy = album.created_by;
  const currentUserId = getCurrentUserId();

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

  // Any member may leave except the album creator. (contract 3.12)
  document.getElementById("leave-album").hidden =
    !currentUserId || String(albumCreatedBy) === String(currentUserId);

  // Only owners may edit the album title. (contract 3.13)
  document.getElementById("edit-album").hidden = album.role !== "owner";

  // Only the album creator may delete the album. (contract 3.14)
  document.getElementById("delete-album").hidden =
    !currentUserId || String(albumCreatedBy) !== String(currentUserId);

  // A pending rename is discarded whenever the album is (re)rendered.
  hideEditForm();
}

function formatJoinedAt(value) {
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : date.toLocaleDateString();
}

function roleButton(label, member, nextRole) {
  const button = document.createElement("button");
  button.type = "button";
  button.className = "ghost small-btn";
  button.textContent = label;
  button.addEventListener("click", () =>
    changeRole(member.user_id, member.name, nextRole, button),
  );
  return button;
}

function removeButton(member) {
  const button = document.createElement("button");
  button.type = "button";
  button.className = "ghost small-btn";
  button.textContent = "Remove";
  button.addEventListener("click", () => removeMember(member, button));
  return button;
}

function renderMembers(members) {
  const list = document.getElementById("member-list");
  list.innerHTML = "";

  if (members.length === 0) {
    const empty = document.createElement("p");
    empty.className = "muted";
    empty.textContent = "No members yet.";
    list.appendChild(empty);
    return;
  }

  const currentUserId = getCurrentUserId();
  const canPromote = currentRole === "owner";
  const isMainOwner = String(albumCreatedBy) === String(currentUserId);

  for (const member of members) {
    const row = document.createElement("div");
    row.className = "member-row";

    const name = document.createElement("span");
    name.className = "member-name";
    name.textContent = member.name;

    const role = document.createElement("span");
    role.className = `badge ${member.role}`;
    role.textContent = member.role;

    const joined = document.createElement("span");
    joined.className = "muted member-joined";
    joined.textContent = `Joined ${formatJoinedAt(member.joined_at)}`;

    row.append(name, role, joined);

    // Promotion: any owner may promote a member. (contract 3.10)
    if (canPromote && member.role === "member") {
      row.appendChild(roleButton("Promote", member, "owner"));
    }

    // Demotion: only the album creator may demote; the creator can never be demoted.
    if (
      isMainOwner &&
      member.role === "owner" &&
      String(member.user_id) !== String(albumCreatedBy)
    ) {
      row.appendChild(roleButton("Demote", member, "member"));
    }

    // Removal: an owner may remove a member; only the album creator may remove
    // another owner. The creator can never be removed, and removing yourself is
    // handled by leaving the album. (contract 3.11)
    const isSelf = String(member.user_id) === String(currentUserId);
    const isCreator = String(member.user_id) === String(albumCreatedBy);
    if (
      currentUserId &&
      canPromote &&
      !isSelf &&
      !isCreator &&
      (member.role !== "owner" || isMainOwner)
    ) {
      row.appendChild(removeButton(member));
    }

    list.appendChild(row);
  }
}

async function loadAlbum(id) {
  try {
    const album = await request(`/album/${id}`);
    renderAlbum(album);
    return album;
  } catch (err) {
    showMessage(err.message);
    return null;
  }
}

async function loadMembers(id) {
  try {
    const members = await request(`/albums/${id}/members`);
    renderMembers(members);
  } catch (err) {
    showMessage(err.message);
  }
}

function renderPhotos(photos) {
  const gallery = document.getElementById("photo-gallery");
  gallery.innerHTML = "";

  if (photos.length === 0) {
    const empty = document.createElement("p");
    empty.className = "muted";
    empty.textContent = "No photos yet. Upload some to see them here.";
    gallery.appendChild(empty);
    return;
  }

  // Each item carries a short-lived pre-signed `url` for direct <img> display.
  // (contract 3.16)
  for (const photo of photos) {
    const tile = document.createElement("figure");
    tile.className = "photo-tile";

    const img = document.createElement("img");
    img.src = photo.url;
    img.alt = `Photo ${photo.id}`;
    img.loading = "lazy";
    // If the pre-signed URL is expired, unreachable, or rejects the request,
    // show a placeholder inside the tile instead of a blank block.
    img.addEventListener("error", () => {
      const fallback = document.createElement("div");
      fallback.className = "fallback";
      fallback.textContent = "Image unavailable";
      tile.replaceChildren(fallback);
    });
    tile.appendChild(img);

    gallery.appendChild(tile);
  }
}

async function loadPhotos(id) {
  try {
    const photos = await request(`/photo/albums/${id}/photos`);
    renderPhotos(photos);
  } catch (err) {
    showMessage(err.message);
  }
}

async function changeRole(userId, name, role, button) {
  button.disabled = true;
  showMessage("");
  try {
    const updated = await request(`/albums/${albumId}/members/${userId}/role`, {
      method: "PATCH",
      body: { role },
    });
    showMessage(`${name} is now ${updated.role}`, "success");
    await Promise.all([loadMembers(albumId), loadAlbum(albumId)]);
  } catch (err) {
    showMessage(err.message);
    button.disabled = false;
  }
}

async function removeMember(member, button) {
  if (!window.confirm(`Remove ${member.name} from this album?`)) return;
  button.disabled = true;
  showMessage("");
  try {
    await request(`/albums/${albumId}/members/${member.user_id}`, {
      method: "DELETE",
    });
    showMessage("Member removed", "success");
    await Promise.all([loadMembers(albumId), loadAlbum(albumId)]);
  } catch (err) {
    showMessage(err.message);
    button.disabled = false;
  }
}

async function leaveAlbum(button) {
  if (!window.confirm("Leave this album?")) return;
  button.disabled = true;
  showMessage("");
  try {
    await request(`/albums/${albumId}/members/me`, { method: "DELETE" });
    window.location.href = "albums.html";
  } catch (err) {
    showMessage(err.message);
    button.disabled = false;
  }
}

function showEditForm() {
  const form = document.getElementById("edit-form");
  const input = document.getElementById("edit-title");
  input.value = document.getElementById("album-title").textContent;
  form.hidden = false;
  input.focus();
  input.select();
}

function hideEditForm() {
  document.getElementById("edit-form").hidden = true;
}

async function handleEditSubmit(event) {
  event.preventDefault();
  const input = document.getElementById("edit-title");
  const title = input.value.trim();
  if (!title) return;

  const submitButton =
    event.submitter || event.target.querySelector('button[type="submit"]');
  if (submitButton) submitButton.disabled = true;
  showMessage("");
  try {
    // PATCH returns the updated album without counts/role; only the title changed.
    const updated = await request(`/albums/${albumId}`, {
      method: "PATCH",
      body: { title },
    });
    document.getElementById("album-title").textContent = updated.title;
    hideEditForm();
    showMessage("Album updated", "success");
  } catch (err) {
    showMessage(err.message);
  } finally {
    if (submitButton) submitButton.disabled = false;
  }
}

async function deleteAlbum(button) {
  if (!window.confirm("Delete this album? This cannot be undone.")) return;
  button.disabled = true;
  showMessage("");
  try {
    await request(`/albums/${albumId}`, { method: "DELETE" });
    window.location.href = "albums.html";
  } catch (err) {
    showMessage(err.message);
    button.disabled = false;
  }
}

async function handleUpload(event) {
  event.preventDefault();
  const input = document.getElementById("photo-files");
  const files = input.files;
  if (!files || files.length === 0) return;

  // The batch endpoint expects repeated `files` form parts. (contract 3.15)
  const formData = new FormData();
  for (const file of files) {
    formData.append("files", file);
  }

  const submitButton =
    event.submitter || event.target.querySelector('button[type="submit"]');
  if (submitButton) submitButton.disabled = true;
  showMessage("");
  try {
    const uploaded = await request(`/photo/albums/${albumId}/photos/batch`, {
      method: "POST",
      body: formData,
    });
    input.value = "";
    const count = Array.isArray(uploaded) ? uploaded.length : 0;
    showMessage(`Uploaded ${count} photo${count === 1 ? "" : "s"}`, "success");
    await Promise.all([loadAlbum(albumId), loadPhotos(albumId)]);
  } catch (err) {
    showMessage(err.message);
  } finally {
    if (submitButton) submitButton.disabled = false;
  }
}

async function init() {
  if (!requireAuth()) return;

  document.getElementById("logout").addEventListener("click", () => {
    clearToken();
    window.location.href = "index.html";
  });

  const leaveButton = document.getElementById("leave-album");
  leaveButton.addEventListener("click", () => leaveAlbum(leaveButton));

  const editButton = document.getElementById("edit-album");
  editButton.addEventListener("click", showEditForm);

  const deleteButton = document.getElementById("delete-album");
  deleteButton.addEventListener("click", () => deleteAlbum(deleteButton));

  document.getElementById("edit-form").addEventListener("submit", handleEditSubmit);
  document.getElementById("edit-cancel").addEventListener("click", hideEditForm);

  document.getElementById("upload-form").addEventListener("submit", handleUpload);

  const id = new URLSearchParams(window.location.search).get("id");
  if (!id) {
    showMessage("No album id provided");
    return;
  }
  albumId = id;
  await loadAlbum(id);
  loadMembers(id);
  loadPhotos(id);
}

init();
