"use strict";

const app = document.querySelector("#app");
const toast = document.querySelector("#toast");
const state = { user: null, csrf: null, route: "here", journal: [], conversations: [] };

function node(tag, attrs = {}, ...children) {
  const element = document.createElement(tag);
  for (const [key, value] of Object.entries(attrs || {})) {
    if (key === "class") element.className = value;
    else if (key === "text") element.textContent = value;
    else if (key.startsWith("on") && typeof value === "function") element.addEventListener(key.slice(2).toLowerCase(), value);
    else if (key === "dataset") Object.assign(element.dataset, value);
    else if (value !== false && value !== null && value !== undefined) element.setAttribute(key, value === true ? "" : String(value));
  }
  for (const child of children.flat()) {
    if (child === null || child === undefined || child === false) continue;
    element.append(child instanceof Node ? child : document.createTextNode(String(child)));
  }
  return element;
}

function showToast(message) {
  toast.textContent = message;
  toast.hidden = false;
  window.clearTimeout(showToast.timer);
  showToast.timer = window.setTimeout(() => { toast.hidden = true; }, 3500);
}

async function api(path, options = {}) {
  const method = options.method || "GET";
  const headers = { Accept: "application/json", ...(options.headers || {}) };
  if (options.body && !(options.body instanceof FormData)) headers["Content-Type"] = "application/json";
  if (!/^(GET|HEAD|OPTIONS)$/i.test(method) && state.csrf) headers["X-CSRF-Token"] = state.csrf;
  const response = await fetch(`/api/v1${path}`, { credentials: "same-origin", ...options, method, headers });
  const contentType = response.headers.get("content-type") || "";
  const payload = contentType.includes("json") && response.status !== 204 ? await response.json() : null;
  if (!response.ok) {
    const error = new Error(payload?.detail || `Request failed (${response.status})`);
    error.status = response.status;
    error.requestId = response.headers.get("x-request-id");
    throw error;
  }
  return payload;
}

function button(label, onClick, variant = "") {
  return node("button", { type: "button", class: `button ${variant}`.trim(), onClick }, label);
}

function field(labelText, name, type = "text", options = {}) {
  const control = type === "textarea"
    ? node("textarea", { name, id: name, placeholder: options.placeholder || "", required: options.required !== false, maxlength: options.maxlength || null })
    : node("input", { name, id: name, type, placeholder: options.placeholder || "", required: options.required !== false, autocomplete: options.autocomplete || null, minlength: options.minlength || null });
  if (options.value !== undefined) control.value = options.value;
  return node("label", {}, labelText, control);
}

function errorBox(error) {
  const suffix = error.requestId ? ` Reference: ${error.requestId}.` : "";
  return node("div", { class: "error-banner", role: "alert" }, `${error.message}${suffix}`);
}

function loading(label = "Loading") {
  return node("div", { class: "empty", role: "status" }, label, node("div", { class: "loading-line", "aria-hidden": "true" }));
}

function pageHead(kicker, title, summary) {
  return node("header", { class: "page-head" }, node("p", { class: "eyebrow", text: kicker }), node("h1", { text: title }), node("p", { text: summary }));
}

function publicNav() {
  return node("nav", { class: "public-nav", "aria-label": "Public navigation" },
    node("a", { href: "/", class: "wordmark" }, "LANSEIR"),
    node("div", { class: "cluster" },
      node("a", { href: "/privacy" }, "Privacy"),
      node("a", { href: "/support" }, "Support"),
      node("a", { href: "/#access", class: "button secondary" }, "Enter")
    )
  );
}

function renderLegal(kind) {
  const content = kind === "privacy" ? [
    ["Private by default", "Captain’s Log, notes, reflections, reading progress, and conversations are scoped to the signed-in account. They are not public or shared by default."],
    ["Minimal collection", "LANSEIR stores account identity, product state, content you intentionally create, operational audit events, and limited AI routing metadata required to run the service."],
    ["Your control", "Account settings provide a portable data export and an authenticated deletion path. Production backups may retain encrypted recovery copies for a bounded operational period."],
    ["AI boundaries", "Only context selected by the active product flow is sent to a configured model provider. Private journal content is not included in AI context by default."],
  ] : [
    ["Use of the service", "Use LANSEIR lawfully and do not attempt to access another person’s account, overload the service, or bypass product entitlements."],
    ["Intellectual property", "VESSEL and associated publishing assets remain protected Sirrah Publishing intellectual property. Access does not transfer ownership or redistribution rights."],
    ["Service condition", "Features may depend on authorized content, configured providers, and operational infrastructure. The interface states those dependencies rather than pretending unavailable capabilities are live."],
    ["Account responsibility", "Protect your credentials and report suspected unauthorized access through Support."],
  ];
  app.replaceChildren(node("div", { class: "public-shell" }, publicNav(), node("main", { id: "main", class: "legal" },
    node("p", { class: "eyebrow" }, "LANSEIR / LEGAL"),
    node("h1", {}, kind === "privacy" ? "Privacy" : "Terms"),
    node("p", { class: "muted" }, "Effective August 28, 2026. Operational policy; formal legal review remains an owner dependency."),
    content.map(([title, text]) => node("section", {}, node("h2", {}, title), node("p", {}, text))),
    node("div", { class: "cluster mt-5" }, node("a", { href: kind === "privacy" ? "/terms" : "/privacy" }, kind === "privacy" ? "Read Terms" : "Read Privacy"), node("a", { href: "/support" }, "Contact Support"))
  )));
}

function renderSupport() {
  const form = node("form", { class: "card stack" },
    field("Email", "email", "email", { autocomplete: "email" }),
    field("Subject", "subject"),
    field("How can we help?", "body", "textarea", { maxlength: 20000 }),
    node("div", { class: "form-status", "aria-live": "polite" }),
    node("button", { class: "button", type: "submit" }, "Send request")
  );
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const status = form.querySelector(".form-status");
    const submit = form.querySelector("button[type=submit]");
    status.replaceChildren(); submit.disabled = true;
    const values = Object.fromEntries(new FormData(form));
    try {
      const result = await api("/support", { method: "POST", body: JSON.stringify(values) });
      status.replaceChildren(node("div", { class: "success-banner" }, `Request ${result.id.slice(0, 8)} received. Keep this reference.`));
      form.reset();
    } catch (error) { status.replaceChildren(errorBox(error)); }
    finally { submit.disabled = false; }
  });
  app.replaceChildren(node("div", { class: "public-shell" }, publicNav(), node("main", { id: "main", class: "legal" },
    node("p", { class: "eyebrow" }, "SUPPORT"), node("h1", {}, "A clear path forward."),
    node("p", { class: "muted measure" }, "Tell us what happened, what you expected, and the route you were using. Do not include passwords, payment details, private keys, or sensitive journal text."), form
  )));
}

function renderPublicNotFound() {
  app.replaceChildren(node("div", { class: "public-shell" }, publicNav(), node("main", { id: "main", class: "legal" },
    node("p", { class: "eyebrow" }, "404 / OFF THE CHART"),
    node("h1", {}, "This passage is not on the current map."),
    node("p", { class: "muted measure" }, "The address may have changed, or the destination may not exist."),
    node("a", { href: "/", class: "button mt-5" }, "Return to LANSEIR")
  )));
}

function renderLanding() {
  let mode = "signin";
  const panel = node("section", { id: "access", class: "auth-panel", "aria-labelledby": "access-title" });
  function drawForm() {
    const tabs = node("div", { class: "tab-list", role: "tablist", "aria-label": "Account access" },
      node("button", { class: "tab", role: "tab", "aria-selected": mode === "signin", onClick: () => { mode = "signin"; drawForm(); } }, "Sign in"),
      node("button", { class: "tab", role: "tab", "aria-selected": mode === "signup", onClick: () => { mode = "signup"; drawForm(); } }, "Create account")
    );
    const form = node("form", { class: "stack" },
      node("div", { class: "stack" }, node("p", { class: "eyebrow" }, mode === "signin" ? "WELCOME BACK" : "BEGIN HERE"), node("h2", { id: "access-title" }, mode === "signin" ? "Return to your passage." : "Create your private space.")),
      ...(mode === "signup" ? [field("Name", "display_name", "text", { autocomplete: "name" })] : []),
      field("Email", "email", "email", { autocomplete: "email" }),
      field("Password", "password", "password", { autocomplete: mode === "signin" ? "current-password" : "new-password", minlength: mode === "signup" ? 12 : 1 }),
      node("div", { class: "form-status", "aria-live": "polite" }),
      node("button", { class: "button", type: "submit" }, mode === "signin" ? "Enter LANSEIR" : "Create account"),
      mode === "signin" ? node("button", { type: "button", class: "link-button", onClick: renderResetRequest }, "Forgot password?") : node("p", { class: "small muted" }, "Use at least 12 characters with upper-case, lower-case, and a number.")
    );
    form.addEventListener("submit", async (event) => {
      event.preventDefault();
      const submit = form.querySelector("button[type=submit]");
      const status = form.querySelector(".form-status");
      submit.disabled = true; status.replaceChildren();
      try {
        const result = await api(mode === "signin" ? "/auth/signin" : "/auth/signup", { method: "POST", body: JSON.stringify(Object.fromEntries(new FormData(form))) });
        state.user = result.user; state.csrf = result.csrf_token; state.route = "here";
        window.location.hash = "here"; renderShell();
      } catch (error) { status.replaceChildren(errorBox(error)); }
      finally { submit.disabled = false; }
    });
    panel.replaceChildren(tabs, form);
  }
  drawForm();
  app.replaceChildren(node("div", { class: "public-shell" }, publicNav(), node("main", { id: "main", class: "hero" },
    node("section", { class: "hero-copy" }, node("p", { class: "eyebrow" }, "LAND · SEA · AIR"), node("h1", {}, "Steady your course."), node("p", {}, "A private, composed environment for reading, reflection, and guided development—supported by CADRE beneath the surface."), node("div", { class: "cluster" }, node("span", { class: "status good" }, "System available"), node("span", { class: "small muted" }, "Your journal remains private by default."))), panel
  )));
}

function renderResetRequest() {
  const form = node("form", { class: "stack" }, node("p", { class: "eyebrow" }, "ACCOUNT RECOVERY"), node("h2", {}, "Reset your password."), field("Email", "email", "email"), node("div", { class: "form-status" }), node("button", { class: "button", type: "submit" }, "Request reset"), node("button", { class: "link-button", type: "button", onClick: renderLanding }, "Back to sign in"));
  form.addEventListener("submit", async (event) => {
    event.preventDefault(); const status = form.querySelector(".form-status");
    try { await api("/auth/password/forgot", { method: "POST", body: JSON.stringify(Object.fromEntries(new FormData(form))) }); status.replaceChildren(node("div", { class: "success-banner" }, "If that account exists, recovery instructions have been prepared.")); }
    catch (error) { status.replaceChildren(errorBox(error)); }
  });
  app.replaceChildren(node("div", { class: "public-shell" }, publicNav(), node("main", { id: "main", class: "hero" }, node("section", { class: "hero-copy" }, node("p", { class: "eyebrow" }, "RECOVERY"), node("h1", {}, "Regain your bearings."), node("p", {}, "Recovery links expire quickly and revoke active sessions when used.")), node("section", { class: "auth-panel" }, form))));
}

const navItems = [
  ["here", "Here"], ["library", "Library"], ["log", "Captain’s Log"], ["voyages", "Voyages"], ["guide", "Guide"], ["settings", "Settings"]
];

function navigate(route) {
  state.route = route; window.location.hash = route; renderCurrent();
}

function navigation(mobile = false) {
  const items = navItems;
  return node("nav", { class: mobile ? "mobile-nav" : "nav-list", "aria-label": mobile ? "Mobile navigation" : "Primary navigation" }, items.map(([route, label]) => node("button", { class: `${mobile ? "" : "nav-link"} ${state.route === route ? "active" : ""}`.trim(), type: "button", onClick: () => navigate(route) }, label)));
}

function renderShell() {
  const sidebar = node("aside", { class: "sidebar" }, node("button", { class: "wordmark wordmark-button", onClick: () => navigate("here") }, "LANSEIR"), navigation(), node("div", { class: "sidebar-foot stack" }, node("p", { class: "small muted" }, "CADRE operating quietly beneath the surface."), node("button", { class: "link-button", onClick: logout }, "Sign out")));
  app.replaceChildren(node("div", { class: "app-shell" }, sidebar, node("div", { class: "app-main" }, node("header", { class: "topbar" }, node("span", { class: "small muted" }, state.user.display_name), node("button", { class: "avatar", type: "button", "aria-label": "Account settings", onClick: () => navigate("settings") }, state.user.display_name.slice(0, 1).toUpperCase())), node("main", { id: "main", class: "page" }), navigation(true))));
  renderCurrent();
}

async function logout() {
  try { await api("/auth/signout", { method: "POST" }); } catch (_) { /* local session is still cleared */ }
  state.user = null; state.csrf = null; history.replaceState(null, "", "/"); renderLanding();
}

function contentRoot() { return document.querySelector("#main"); }

async function renderCurrent() {
  document.querySelectorAll(".nav-link,.mobile-nav button").forEach((item) => item.classList.toggle("active", item.textContent.toLowerCase().replace("captain’s ", "") === state.route));
  const routes = { here: renderHere, library: renderLibrary, log: renderJournal, voyages: renderVoyages, guide: renderGuide, settings: renderSettings, mission: renderMission };
  const renderer = routes[state.route];
  if (!renderer || (state.route === "mission" && state.user.role !== "admin")) return renderNotFound();
  contentRoot().replaceChildren(loading());
  try { await renderer(); } catch (error) {
    if (error.status === 401) return logout();
    contentRoot().replaceChildren(pageHead("SYSTEM", "We lost the channel.", "Your work was not intentionally discarded."), errorBox(error), button("Try again", renderCurrent, "secondary"));
  }
}

async function renderHere() {
  const [library, voyages] = await Promise.all([api("/library"), api("/voyages")]);
  const vessel = library.find((item) => item.slug === "vessel-mastering-the-ship-of-self");
  const active = voyages.find((item) => item.enrollment?.status === "active");
  const main = contentRoot();
  main.replaceChildren(pageHead("HERE / NOW", `Welcome, ${state.user.display_name}.`, "See present reality clearly, then move one meaningful thing forward."), node("div", { class: "grid" },
    node("section", { class: "card span-8" }, node("div", { class: "split" }, node("div", { class: "stack" }, node("p", { class: "eyebrow" }, "FLAGSHIP LIBRARY"), node("h2", {}, vessel?.title || "VESSEL"), node("p", { class: "muted" }, vessel?.subtitle || "Mastering the Ship of Self")), node("span", { class: "status" }, vessel?.content_access || (vessel?.state === "available" ? "Available" : "Source protected"))), vessel?.progress ? progressBar(vessel.progress.percent) : node("p", { class: "small muted" }, "Reading begins when the authorized manuscript is promoted."), button("Open library", () => navigate("library"), "secondary")),
    node("section", { class: "card span-4" }, node("p", { class: "eyebrow" }, "YOUR COURSE"), node("p", { class: "stat" }, active ? `${active.enrollment.completed_lesson_ids.length}/${active.lessons.length}` : "Ready"), node("p", { class: "muted" }, active ? `Continue ${active.title}.` : "Begin a guided Voyage when you are ready."), button(active ? "Resume Voyage" : "View Voyages", () => navigate("voyages"), "secondary")),
    node("section", { class: "card span-4 interactive", role: "button", tabindex: "0", onClick: () => navigate("log"), onKeydown: (e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); navigate("log"); } } }, node("p", { class: "eyebrow" }, "PRIVATE"), node("h3", {}, "Captain’s Log"), node("p", { class: "muted" }, "Record what is true before deciding what comes next.")),
    node("section", { class: "card span-4 interactive", role: "button", tabindex: "0", onClick: () => navigate("guide"), onKeydown: (e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); navigate("guide"); } } }, node("p", { class: "eyebrow" }, "REFLECTION"), node("h3", {}, "LANSEIR Guide"), node("p", { class: "muted" }, "Use authorized context without exposing your private journal by default.")),
    node("section", { class: "card span-4" }, node("p", { class: "eyebrow" }, "ACCOUNT"), node("h3", {}, state.user.email_verified_at ? "Identity verified" : "Verification pending"), node("p", { class: "muted" }, state.user.email_verified_at ? "Your account email is verified." : "Email delivery requires the configured production mail provider."), button("Account settings", () => navigate("settings"), "secondary"))
  ));
}

function progressBar(percent) {
  const fill = node("div", { class: "progress-fill" }); fill.style.width = `${Math.max(0, Math.min(100, percent))}%`;
  return node("div", { class: "stack" }, node("div", { class: "split small" }, node("span", {}, "Progress"), node("span", {}, `${Math.round(percent)}%`)), node("div", { class: "progress-track" }, fill));
}

async function renderLibrary() {
  const books = await api("/library"); const main = contentRoot();
  main.replaceChildren(pageHead("LIBRARY", "Works worth returning to.", "Your reading position, notes, and bookmarks remain attached to your account."));
  if (!books.length) return main.append(node("div", { class: "empty" }, "No titles are currently available."));
  main.append(node("div", { class: "grid" }, books.map((book) => node(
    "article",
    { class: "card span-6" },
    node("p", { class: "eyebrow" }, book.publisher),
    node("h2", {}, book.title),
    node("p", { class: "muted" }, book.subtitle),
    node("p", {}, book.description),
    book.progress ? progressBar(book.progress.percent) : null,
    node(
      "div",
      { class: "split" },
      node("span", { class: "status" }, book.state === "available" ? (book.entitlement ? "In your library" : "Access required") : "Awaiting authorized source"),
      button("Open", () => renderBook(book.slug), "secondary")
    )
  ))));
}

async function renderBook(slug) {
  contentRoot().replaceChildren(loading("Opening title…"));
  try {
    const book = await api(`/books/${encodeURIComponent(slug)}`);
    const main = contentRoot();
    const back = button("Back to library", renderLibrary, "secondary");
    if (!book.chapters.length) {
      main.replaceChildren(pageHead(book.publisher, book.title, book.subtitle), node("section", { class: "card" }, node("h2", {}, "The source remains protected."), node("p", { class: "muted measure" }, book.content_access === "entitlement_required" ? "This edition is available, but your account does not yet have an active entitlement." : "No manuscript approximation has been inserted. Reading will activate only after the authorized Sirrah Publishing source is ingested and explicitly promoted."), back));
      return;
    }
    let current = book.chapters.find((chapter) => chapter.id === book.progress?.chapter_id) || book.chapters[0];
    const reader = node("section", { class: "reader stack-lg" });
    function draw() {
      const selector = node("select", { "aria-label": "Chapter" }, book.chapters.map((chapter) => node("option", { value: chapter.id }, `${chapter.position}. ${chapter.title}`)));
      selector.value = current.id;
      selector.addEventListener("change", () => { current = book.chapters.find((chapter) => chapter.id === selector.value); draw(); });
      const save = button("Save position", async () => {
        await api(`/books/${book.id}/progress`, { method: "PUT", body: JSON.stringify({ chapter_id: current.id, percent: Math.round((current.position / book.chapters.length) * 100), locator: `chapter:${current.position}`, audio_seconds: 0, playback_rate: 1 }) }); showToast("Reading position saved.");
      });
      reader.replaceChildren(node("div", { class: "split" }, back, selector), node("div", { class: "stack-lg" }, node("p", { class: "eyebrow" }, book.title), node("h1", {}, current.title), node("div", { class: "reader-body" }, current.body)), node("div", { class: "cluster" }, save, button("Add bookmark", async () => { await api("/bookmarks", { method: "POST", body: JSON.stringify({ book_id: book.id, chapter_id: current.id, locator: `chapter:${current.position}`, label: current.title }) }); showToast("Bookmark saved."); }, "secondary")));
    }
    draw(); main.replaceChildren(reader);
  } catch (error) { contentRoot().replaceChildren(errorBox(error), button("Back", renderLibrary, "secondary")); }
}

async function renderJournal() {
  state.journal = await api("/captains-log"); let selected = state.journal[0] || null;
  const main = contentRoot();
  function draw() {
    const list = node("div", { class: "list" }, state.journal.length ? state.journal.map((entry) => node("button", { class: `list-item ${selected?.id === entry.id ? "active" : ""}`, onClick: () => { selected = entry; draw(); } }, node("strong", {}, entry.title), node("span", { class: "small muted" }, new Date(entry.updated_at).toLocaleString()))) : node("div", { class: "empty" }, "Your log is empty. Begin with what is true now."));
    const editor = node("section", { class: "card editor-card" });
    if (!selected) editor.append(node("p", { class: "eyebrow" }, "PRIVATE BY DEFAULT"), node("h2", {}, "Begin an entry."), node("p", { class: "muted" }, "Nothing is shared or sent to the Reflection Guide unless you choose a separate context flow."), button("New entry", createEntry));
    else {
      const form = node("form", { class: "stack" }, field("Title", "title", "text", { value: selected.title }), field("Entry", "body", "textarea", { value: selected.body, required: false, maxlength: 100000 }), node("p", { class: "small muted" }, "Manual save is dependable; this editor does not claim autosave."), node("div", { class: "form-status" }), node("div", { class: "cluster" }, node("button", { class: "button", type: "submit" }, "Save entry"), button("Delete", deleteEntry, "danger")));
      form.addEventListener("submit", async (event) => { event.preventDefault(); const values = Object.fromEntries(new FormData(form)); try { const updated = await api(`/captains-log/${selected.id}`, { method: "PUT", body: JSON.stringify({ ...values, prompt: selected.prompt || "" }) }); state.journal = state.journal.map((item) => item.id === updated.id ? updated : item); selected = updated; showToast("Entry saved."); draw(); } catch (error) { form.querySelector(".form-status").replaceChildren(errorBox(error)); } });
      editor.append(form);
    }
    main.replaceChildren(pageHead("CAPTAIN’S LOG", "Private reflection, held with care.", "Record, revise, search, and return. Your entries are isolated to your account."), node("div", { class: "cluster mb-3" }, button("New entry", createEntry), button("Search", searchEntries, "secondary")), node("div", { class: "editor-layout" }, list, editor));
  }
  async function createEntry() { const entry = await api("/captains-log", { method: "POST", body: JSON.stringify({ title: "New entry", body: "", prompt: "What is true now?" }) }); state.journal.unshift(entry); selected = entry; draw(); }
  async function deleteEntry() { if (!window.confirm("Delete this private entry permanently?")) return; await api(`/captains-log/${selected.id}`, { method: "DELETE" }); state.journal = state.journal.filter((item) => item.id !== selected.id); selected = state.journal[0] || null; showToast("Entry deleted."); draw(); }
  async function searchEntries() { const query = window.prompt("Search your private log"); if (query === null) return; state.journal = await api(`/captains-log?query=${encodeURIComponent(query)}`); selected = state.journal[0] || null; draw(); }
  draw();
}

async function renderVoyages() {
  const voyages = await api("/voyages"); const main = contentRoot();
  main.replaceChildren(pageHead("VOYAGES", "Development with a discernible course.", "Each Voyage remembers your progress and reflections across sessions."));
  if (!voyages.length) return main.append(node("div", { class: "empty" }, "No Voyages are available."));
  main.append(node("div", { class: "stack-lg" }, voyages.map((voyage) => voyageCard(voyage))));
}

function voyageCard(voyage) {
  const holder = node("section", { class: "card" });
  function draw(current) {
    const enrollment = current.enrollment;
    const lessons = node("div", { class: "stack-lg" }, current.lessons.map((lesson) => {
      const isCurrent = enrollment?.status === "active" && enrollment.current_lesson_id === lesson.id;
      const canEdit = lesson.completed || isCurrent;
      const textarea = node("textarea", { placeholder: lesson.prompt, "aria-label": `Reflection for ${lesson.title}` }); textarea.value = lesson.reflection || "";
      const save = button(lesson.completed ? "Update reflection" : "Save and complete", async () => { if (!textarea.value.trim()) return showToast("Write a reflection before completing this lesson."); const updated = await api(`/voyages/${current.id}/lessons/${lesson.id}/reflection`, { method: "PUT", body: JSON.stringify({ body: textarea.value, complete: true }) }); current = updated; showToast("Voyage progress saved."); draw(current); });
      return node("article", { class: "lesson stack", dataset: { step: String(lesson.position).padStart(2, "0") } }, node("div", { class: "split" }, node("h3", {}, lesson.title), lesson.completed ? node("span", { class: "status good" }, "Complete") : node("span", { class: "status" }, isCurrent ? "Current watch" : "Ahead")), node("p", { class: "muted measure" }, lesson.guidance), canEdit ? node("label", {}, lesson.prompt, textarea) : node("p", { class: "small muted" }, "Complete the current watch to unlock this reflection."), canEdit ? save : null);
    }));
    const children = [
      node("div", { class: "split" }, node("div", { class: "stack" }, node("p", { class: "eyebrow" }, "GUIDED DEVELOPMENT"), node("h2", {}, current.title), node("p", { class: "muted measure" }, current.description)), enrollment ? node("span", { class: `status ${enrollment.status === "completed" ? "good" : ""}` }, enrollment.status) : button("Begin Voyage", async () => { current = await api(`/voyages/${current.id}/enroll`, { method: "POST" }); showToast("Voyage begun."); draw(current); })),
      enrollment ? progressBar((enrollment.completed_lesson_ids.length / Math.max(1, current.lessons.length)) * 100) : null,
      enrollment ? lessons : null,
    ].filter(Boolean);
    holder.replaceChildren(...children);
  }
  draw(voyage); return holder;
}

async function renderGuide() {
  state.conversations = await api("/ai/conversations"); let selected = state.conversations[0] || null; const main = contentRoot();
  async function ensureConversation() { if (selected) return selected; selected = await api("/ai/conversations", { method: "POST", body: JSON.stringify({ title: "Reflection", context_kind: "general", context_id: null }) }); state.conversations.unshift(selected); return selected; }
  async function draw() {
    const conversation = selected ? await api(`/ai/conversations/${selected.id}`) : { messages: [] };
    const list = node("div", { class: "message-list", "aria-live": "polite" }, conversation.messages.length ? conversation.messages.map((message) => node("div", { class: `message ${message.role}` }, message.content)) : node("div", { class: "empty" }, "Begin with a situation, a decision, or the next action you need to see clearly."));
    const form = node("form", { class: "stack" }, field("Your message", "content", "textarea", { placeholder: "What needs clarity?", maxlength: 8000 }), node("div", { class: "form-status" }), node("button", { class: "button", type: "submit" }, "Reflect"));
    form.addEventListener("submit", async (event) => { event.preventDefault(); const submit = form.querySelector("button"); const status = form.querySelector(".form-status"); submit.disabled = true; status.replaceChildren(); try { const target = await ensureConversation(); await api(`/ai/conversations/${target.id}/messages`, { method: "POST", body: JSON.stringify(Object.fromEntries(new FormData(form))) }); form.reset(); await draw(); } catch (error) { status.replaceChildren(errorBox(error)); } finally { submit.disabled = false; } });
    main.replaceChildren(pageHead("REFLECTION GUIDE", "Clarity without theater.", "The local guide is available at zero provider cost. Configured model providers remain server-side, explicit, and inspectable."), node("div", { class: "grid" }, node("section", { class: "card span-8" }, list, form), node("aside", { class: "card span-4" }, node("p", { class: "eyebrow" }, "CONTEXT BOUNDARY"), node("h3", {}, "You decide what crosses."), node("p", { class: "muted" }, "Captain’s Log is excluded by default. The guide can use only context attached to this conversation flow."), node("span", { class: "status good" }, "Local policy active"))));
  }
  await draw();
}

async function renderSettings() {
  const main = contentRoot(); const profile = node("form", { class: "card stack" }, node("h2", {}, "Profile"), field("Display name", "display_name", "text", { value: state.user.display_name }), node("div", { class: "form-status" }), node("button", { class: "button", type: "submit" }, "Save profile"));
  profile.addEventListener("submit", async (event) => { event.preventDefault(); try { state.user = await api("/me", { method: "PATCH", body: JSON.stringify(Object.fromEntries(new FormData(profile))) }); showToast("Profile saved."); renderShell(); } catch (error) { profile.querySelector(".form-status").replaceChildren(errorBox(error)); } });
  const password = node("form", { class: "card stack" }, node("h2", {}, "Password"), field("Current password", "current_password", "password"), field("New password", "new_password", "password", { minlength: 12 }), node("div", { class: "form-status" }), node("button", { class: "button", type: "submit" }, "Change password"));
  password.addEventListener("submit", async (event) => { event.preventDefault(); try { await api("/me/password", { method: "POST", body: JSON.stringify(Object.fromEntries(new FormData(password))) }); password.reset(); showToast("Password changed."); } catch (error) { password.querySelector(".form-status").replaceChildren(errorBox(error)); } });
  const control = node("section", { class: "card stack" }, node("h2", {}, "Data control"), node("p", { class: "muted" }, "Export a portable JSON record of your account and private product state."), button("Export my data", async () => { const data = await api("/me/export"); const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" }); const link = node("a", { href: URL.createObjectURL(blob), download: `lanseir-export-${new Date().toISOString().slice(0, 10)}.json` }); document.body.append(link); link.click(); link.remove(); }, "secondary"), node("a", { href: "/privacy" }, "Read privacy boundaries"));
  const deletion = node("form", { class: "card stack" }, node("p", { class: "eyebrow" }, "IRREVERSIBLE"), node("h2", {}, "Delete account"), node("p", { class: "muted" }, "Confirm the signed-in email and password. Active account data will be deleted; protected operational backups follow their governed retention policy."), field("Email", "email", "email", { value: state.user.email }), field("Password", "password", "password"), node("div", { class: "form-status" }), node("button", { class: "button secondary", type: "submit" }, "Delete my account"));
  deletion.addEventListener("submit", async (event) => {
    event.preventDefault();
    const status = deletion.querySelector(".form-status");
    try {
      await api("/me", { method: "DELETE", body: JSON.stringify(Object.fromEntries(new FormData(deletion))) });
      state.user = null; state.csrf = null; history.replaceState(null, "", "/"); renderLanding();
    } catch (error) { status.replaceChildren(errorBox(error)); }
  });
  const operational = state.user.role === "admin" ? node("section", { class: "card stack" }, node("p", { class: "eyebrow" }, "ADMIN"), node("h2", {}, "Mission Control"), node("p", { class: "muted" }, "Inspect actual system state, specialist definitions, runs, and failures."), button("Open Mission Control", () => navigate("mission"), "secondary")) : null;
  main.replaceChildren(pageHead("SETTINGS", "Your account, under your control.", state.user.email), node("div", { class: "grid" }, node("div", { class: "span-6 stack" }, profile, control), node("div", { class: "span-6 stack" }, password, operational || node("section", { class: "card" }, node("p", { class: "eyebrow" }, "SUPPORT"), node("h3", {}, "Need a hand?"), node("a", { href: "/support" }, "Open Support")), deletion)));
}

async function renderMission() {
  const data = await api("/admin/mission-control"); const main = contentRoot();
  const missionRows = data.missions.length ? node("div", { class: "list" }, data.missions.map((mission) => {
    const fix = mission.fix_available ? button("FIX", async () => {
      await api(`/admin/missions/${mission.id}/fix`, { method: "POST" });
      showToast("Recovery mission dispatched to Al.");
      await renderMission();
    }, "secondary") : null;
    return node("div", { class: "list-item" }, node("div", { class: "split" }, node("strong", {}, mission.title), node("span", { class: `status ${mission.status === "verified" ? "good" : ""}` }, mission.status)), node("p", { class: "small muted" }, `${mission.specialist} · ${mission.failure_class || "no failure"}`), mission.root_cause ? node("p", {}, mission.root_cause) : null, fix);
  })) : node("div", { class: "empty" }, "No approved missions are queued.");
  const evidenceRows = data.evidence.length ? node("div", { class: "list" }, data.evidence.map((item) => node("div", { class: "list-item" }, node("div", { class: "split" }, node("strong", {}, item.kind.replaceAll("_", " ")), node("span", { class: `status ${item.passed ? "good" : ""}` }, item.passed ? "verified evidence" : "failure evidence")), node("p", {}, item.summary), item.locator ? node("p", { class: "small muted" }, item.locator) : null))) : node("div", { class: "empty" }, "No material evidence has been recorded.");
  main.replaceChildren(
    pageHead("CADRE / MISSION CONTROL", "System truth, not theater.", `${data.environment} · release ${data.release}`),
    node("div", { class: "grid" }, Object.entries(data.counts).map(([key, value]) => node("section", { class: "card span-3" }, node("p", { class: "eyebrow" }, key.replaceAll("_", " ")), node("p", { class: "stat" }, value)))),
    node("section", { class: "card mt-3" }, node("h2", {}, "Approved mission execution"), missionRows),
    node("section", { class: "card mt-3" }, node("h2", {}, "Evidence ledger"), evidenceRows),
    node("section", { class: "card mt-3" }, node("div", { class: "split" }, node("div", {}, node("p", { class: "eyebrow" }, "ROUTING POLICY"), node("h2", {}, `${data.ai_policy.provider} / ${data.ai_policy.model}`)), node("span", { class: "status good" }, `${data.ai_policy.daily_message_limit} messages/day`))),
    node("div", { class: "grid mt-3" }, data.specialists.map((item) => node("section", { class: "card span-4" }, node("p", { class: "eyebrow" }, item.key), node("h3", {}, item.name), node("p", { class: "muted" }, item.responsibility), node("p", { class: "small" }, `Routes: ${item.routing_criteria.join(", ")}`)))),
    node("section", { class: "card mt-3" }, node("h2", {}, "Recent runs"), data.recent_runs.length ? node("div", { class: "list" }, data.recent_runs.map((run) => node("div", { class: "list-item" }, node("div", { class: "split" }, node("strong", {}, `${run.specialist} · ${run.task_kind}`), node("span", { class: `status ${run.status === "completed" ? "good" : ""}` }, run.status)), node("span", { class: "small muted" }, `${run.provider || "unassigned"} / ${run.model || "unassigned"} · ${run.latency_ms || 0}ms`)))) : node("div", { class: "empty" }, "No execution runs have been recorded."))
  );
}

function renderNotFound() {
  contentRoot().replaceChildren(pageHead("404", "This route is off the chart.", "The requested destination is not part of the current product map."), button("Return Here", () => navigate("here")));
}

async function bootstrap() {
  const path = window.location.pathname;
  if (path === "/privacy") return renderLegal("privacy");
  if (path === "/terms") return renderLegal("terms");
  if (path === "/support") return renderSupport();
  if (path !== "/" && path !== "/app") return renderPublicNotFound();
  try {
    const session = await api("/auth/session");
    if (session.authenticated) {
      state.user = session.user; state.csrf = session.csrf_token;
      state.route = window.location.hash.slice(1) || "here"; renderShell();
    } else renderLanding();
  } catch (_) { renderLanding(); }
  app.setAttribute("aria-busy", "false");
}

window.addEventListener("hashchange", () => {
  if (!state.user) return;
  state.route = window.location.hash.slice(1) || "here"; renderCurrent();
});

bootstrap();
