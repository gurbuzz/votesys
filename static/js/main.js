// static/js/main.js
function session() {
  return {
    token:    localStorage.getItem("token"),
    role:     localStorage.getItem("role")    || "guest",
    username: localStorage.getItem("username")|| ""
  };
}

function renderNavbar() {
  const { token, role } = session();
  document.querySelectorAll("#nav-items [data-role]").forEach(el => {
    const r = el.dataset.role;
    el.style.display = "";                           // önce hepsini aç
    if (r === "guest" && token)            el.style.display = "none";
    if (r === "auth"  && !token)           el.style.display = "none";
    if (r === "admin" && role !== "admin") el.style.display = "none";
  });
}

function logout() {
  ["token","username","role"].forEach(k => localStorage.removeItem(k));
  renderNavbar();
  window.location.href = "/";
}

async function fetchAuth(url, opts = {}) {
  const { token } = session();
  opts.headers = opts.headers || {};
  if (!opts.headers["Content-Type"] && !(opts.body instanceof FormData)) {
    opts.headers["Content-Type"] = "application/json";
  }
  if (token) opts.headers["Authorization"] = "Bearer " + token;
  return fetch(url, opts);
}

// client-side koruma ♟
function requireAuth(needAdmin = false) {
  const { token, role } = session();
  if (!token || (needAdmin && role !== "admin")) {
    window.location.href = "/login";
    return false;
  }
  return true;
}

document.addEventListener("DOMContentLoaded", renderNavbar);
