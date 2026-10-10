import { request, setToken, redirectIfAuthed } from "./api.js";

function showMessage(text, kind = "error") {
  const el = document.getElementById("message");
  el.textContent = text;
  el.className = `message ${kind}`;
  el.hidden = !text;
}

function setBusy(busy) {
  document.querySelectorAll("button").forEach((b) => {
    b.disabled = busy;
  });
}

async function handleSignup(event) {
  event.preventDefault();
  const name = document.getElementById("signup-name").value.trim();
  const email = document.getElementById("signup-email").value.trim();
  const password = document.getElementById("signup-password").value;

  setBusy(true);
  showMessage("");
  try {
    await request("/signup", {
      method: "POST",
      auth: false,
      body: { name, email, password },
    });
    const token = await request("/login", {
      method: "POST",
      auth: false,
      body: { email, password },
    });
    setToken(token.access_token);
    window.location.href = "albums.html";
  } catch (err) {
    showMessage(err.message);
  } finally {
    setBusy(false);
  }
}

async function handleLogin(event) {
  event.preventDefault();
  const email = document.getElementById("login-email").value.trim();
  const password = document.getElementById("login-password").value;

  setBusy(true);
  showMessage("");
  try {
    const token = await request("/login", {
      method: "POST",
      auth: false,
      body: { email, password },
    });
    setToken(token.access_token);
    window.location.href = "albums.html";
  } catch (err) {
    showMessage(err.message);
  } finally {
    setBusy(false);
  }
}

function showTab(tab) {
  const isLogin = tab === "login";
  document.getElementById("login-form").hidden = !isLogin;
  document.getElementById("signup-form").hidden = isLogin;
  document.getElementById("tab-login").classList.toggle("active", isLogin);
  document.getElementById("tab-signup").classList.toggle("active", !isLogin);
  showMessage("");
}

function init() {
  if (redirectIfAuthed()) {
    return;
  }
  document.getElementById("tab-login").addEventListener("click", () => showTab("login"));
  document.getElementById("tab-signup").addEventListener("click", () => showTab("signup"));
  document.getElementById("login-form").addEventListener("submit", handleLogin);
  document.getElementById("signup-form").addEventListener("submit", handleSignup);
  showTab("login");
}

init();
