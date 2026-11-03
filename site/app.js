(function () {
  "use strict";

  var D = window.CAUGHT_UP;
  var KEY = "caughtup:v1";
  var $ = function (id) { return document.getElementById(id); };

  // ---- state (per browser, no login) ----
  function load() {
    try { return JSON.parse(localStorage.getItem(KEY)) || { watched: {} }; }
    catch (e) { return { watched: {} }; }
  }
  function save() {
    try { localStorage.setItem(KEY, JSON.stringify(state)); } catch (e) { /* private mode: fine */ }
  }
  var state = load();
  if (!state.watched) state.watched = {};

  var path = [];
  D.levels.forEach(function (lvl) {
    lvl.videos.forEach(function (v) { path.push({ v: v, level: lvl }); });
  });

  // ---- helpers ----
  function el(tag, attrs, kids) {
    var n = document.createElement(tag);
    Object.keys(attrs || {}).forEach(function (k) {
      if (k === "text") n.textContent = attrs[k];
      else if (k === "class") n.className = attrs[k];
      else n.setAttribute(k, attrs[k]);
    });
    (kids || []).forEach(function (c) { if (c) n.appendChild(c); });
    return n;
  }
  function fmtDur(s) {
    if (!s) return "";
    var h = Math.floor(s / 3600), m = Math.floor((s % 3600) / 60), sec = s % 60;
    var mm = h ? String(m).padStart(2, "0") : String(m);
    return (h ? h + ":" : "") + mm + ":" + String(sec).padStart(2, "0");
  }
  function hours(s) {
    var h = s / 3600;
    return h < 1 ? Math.round(s / 60) + " min" : (Math.round(h * 2) / 2) + " hours";
  }
  function thumb(vid) {
    // hq2 is a frame YouTube grabs from the middle of the video, not the uploaded thumbnail.
    var img = el("img", { src: "https://i.ytimg.com/vi/" + vid + "/hq2.jpg", alt: "", loading: "lazy" });
    img.addEventListener("error", function () {
      if (img.src.indexOf("hqdefault") === -1) img.src = "https://i.ytimg.com/vi/" + vid + "/hqdefault.jpg";
    }, { once: false });
    return img;
  }
  function checkIcon() {
    var s = document.createElementNS("http://www.w3.org/2000/svg", "svg");
    s.setAttribute("viewBox", "0 0 24 24"); s.setAttribute("width", "44"); s.setAttribute("height", "44");
    s.innerHTML = '<path d="M5 12.5l4.5 4.5L19 7.5" fill="none" stroke="currentColor" stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round"/>';
    return s;
  }

  // ---- render ----
  function card(v, num, levelName) {
    var b = el("button", { class: "card", type: "button", "data-vid": v.vid, "aria-label": (num ? num + ". " : "") + v.title });
    var t = el("div", { class: "thumb" }, [thumb(v.vid)]);
    if (num) t.appendChild(el("span", { class: "num", text: String(num) }));
    if (v.duration) t.appendChild(el("span", { class: "dur", text: fmtDur(v.duration) }));
    var chk = el("span", { class: "check" }); chk.appendChild(checkIcon()); t.appendChild(chk);
    b.appendChild(t);
    b.appendChild(el("h3", { text: v.title }));
    b.appendChild(el("p", { class: "channel", text: v.channel }));
    if (v.why) b.appendChild(el("p", { class: "why", text: v.why }));
    if (v.signal) b.appendChild(el("p", { class: "signal", text: v.signal }));
    b.addEventListener("click", function () { openPlayer(v, levelName); });
    return b;
  }

  function render() {
    $("updated").textContent = "Updated " + D.updated;
    $("lede").textContent = D.lede;

    var total = path.reduce(function (s, p) { return s + (p.v.duration || 0); }, 0);
    var stats = [
      ["" + path.length, "videos"],
      ["" + D.levels.length, "levels, in order"],
    ];
    if (total && path.every(function (p) { return p.v.duration; })) stats.push(["~" + hours(total), "total"]);
    stats.push(["0", "logins"]);
    stats.forEach(function (s) {
      var li = el("li"); li.appendChild(el("b", { text: s[0] })); li.appendChild(document.createTextNode(" " + s[1]));
      $("stats").appendChild(li);
    });

    var n = 0;
    var wrap = $("levels");
    D.levels.forEach(function (lvl) {
      var sec = el("section", { class: "level", id: "level-" + lvl.id });
      var head = el("div", { class: "section-head" });
      var tag = el("div", { class: "level-tag" }, [
        el("span", { class: "eyebrow", text: "Level " + lvl.id }),
        el("span", { class: "level-count", "data-level": String(lvl.id) }),
      ]);
      head.appendChild(tag);
      head.appendChild(el("h2", { text: lvl.name }));
      head.appendChild(el("p", { text: lvl.goal }));
      sec.appendChild(head);
      var grid = el("div", { class: "grid" });
      lvl.videos.forEach(function (v) { n += 1; grid.appendChild(card(v, n, "Level " + lvl.id + " · " + lvl.name)); });
      sec.appendChild(grid);
      if (lvl.note) {
        var a = el("a", { class: "btn primary", href: lvl.note.url, target: "_blank", rel: "noopener", text: lvl.note.cta });
        var p = el("p"); p.appendChild(el("b", { text: lvl.note.title })); p.appendChild(document.createTextNode(lvl.note.body));
        sec.appendChild(el("aside", { class: "note" }, [p, a]));
      }
      wrap.appendChild(sec);
    });

    if (D.thisMonth && D.thisMonth.length) {
      $("this-month").hidden = false;
      D.thisMonth.forEach(function (v) { $("month-grid").appendChild(card(v, null, "New this month")); });
    }

    var m = $("method");
    D.method.intro.forEach(function (t) { m.appendChild(el("p", { text: t })); });
    var ol = el("ol"); D.method.steps.forEach(function (t) { ol.appendChild(el("li", { text: t })); }); m.appendChild(ol);
    D.method.outro.forEach(function (t) { m.appendChild(el("p", { text: t })); });

    var f = $("footer");
    D.credits.forEach(function (c) {
      var p = el("p");
      c.forEach(function (part) {
        p.appendChild(part.url ? el("a", { href: part.url, target: "_blank", rel: "noopener", text: part.text }) : document.createTextNode(part.text));
      });
      f.appendChild(p);
    });

    refresh();
  }

  function refresh() {
    var done = path.filter(function (p) { return state.watched[p.v.vid]; }).length;
    $("progress-fill").style.width = (100 * done / path.length) + "%";
    $("progress-label").textContent = done === path.length ? "Caught up" : done + " of " + path.length;
    document.querySelectorAll(".card").forEach(function (c) {
      c.classList.toggle("watched", !!state.watched[c.getAttribute("data-vid")]);
    });
    D.levels.forEach(function (lvl) {
      var c = lvl.videos.filter(function (v) { return state.watched[v.vid]; }).length;
      var tag = document.querySelector('.level-count[data-level="' + lvl.id + '"]');
      tag.textContent = c === lvl.videos.length ? "· done" : "· " + c + "/" + lvl.videos.length;
      tag.classList.toggle("done", c === lvl.videos.length);
    });
    $("start").textContent = done === 0 ? "Start watching" : done === path.length ? "Rewatch from the top" : "Continue where you left off";
  }

  // ---- player ----
  var current = null;
  function openPlayer(v, levelName) {
    current = v;
    $("player-frame").src = "https://www.youtube-nocookie.com/embed/" + v.vid + "?autoplay=1&rel=0";
    $("player-level").textContent = levelName;
    $("player-title").textContent = v.title;
    $("player-channel").textContent = v.channel;
    $("player-why").textContent = v.why || "";
    var q = $("player-quote");
    q.textContent = "";
    q.hidden = !v.quote;
    if (v.quote) {
      q.appendChild(el("p", { text: "“" + v.quote.text + "”" }));
      var cite = el("p", { class: "cite" });
      cite.appendChild(document.createTextNode("— "));
      cite.appendChild(el("a", { href: "https://news.ycombinator.com/item?id=" + v.quote.hn, target: "_blank", rel: "noopener", text: "a Hacker News comment, " + v.quote.year }));
      q.appendChild(cite);
    }
    $("player-yt").href = "https://www.youtube.com/watch?v=" + v.vid;
    var inPath = path.some(function (p) { return p.v.vid === v.vid; });
    $("player-done").textContent = state.watched[v.vid] ? (inPath ? "Next video" : "Close") : (inPath ? "Mark watched & next" : "Mark watched");
    if (!$("player").open) $("player").showModal();
  }
  function closePlayer() {
    $("player-frame").src = "about:blank";
    if ($("player").open) $("player").close();
  }
  function nextUnwatched(after) {
    var start = 0;
    if (after) path.forEach(function (p, i) { if (p.v.vid === after) start = i + 1; });
    for (var k = 0; k < path.length; k++) {
      var p = path[(start + k) % path.length];
      if (!state.watched[p.v.vid]) return p;
    }
    return null;
  }

  $("player-close").addEventListener("click", closePlayer);
  $("player").addEventListener("close", function () { $("player-frame").src = "about:blank"; });
  $("player").addEventListener("click", function (e) { if (e.target === $("player")) closePlayer(); });
  $("player-done").addEventListener("click", function () {
    if (!current) return;
    state.watched[current.vid] = Date.now(); save(); refresh();
    var inPath = path.some(function (p) { return p.v.vid === current.vid; });
    var nxt = inPath ? nextUnwatched(current.vid) : null;
    if (nxt) openPlayer(nxt.v, "Level " + nxt.level.id + " · " + nxt.level.name);
    else closePlayer();
  });
  $("start").addEventListener("click", function () {
    var nxt = nextUnwatched(null) || path[0];
    openPlayer(nxt.v, "Level " + nxt.level.id + " · " + nxt.level.name);
  });

  render();
})();
