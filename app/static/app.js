(() => {
  "use strict";

  const state = {
    data: null,
    url: "",
    query: "",
  };

  const elements = {
    form: document.querySelector("#transcript-form"),
    url: document.querySelector("#youtube-url"),
    preferredLanguage: document.querySelector("#preferred-language"),
    generateButton: document.querySelector("#generate-button"),
    message: document.querySelector("#message"),
    result: document.querySelector("#result"),
    player: document.querySelector("#player"),
    videoTitle: document.querySelector("#video-title"),
    videoAuthor: document.querySelector("#video-author"),
    languagePill: document.querySelector("#language-pill"),
    segmentCount: document.querySelector("#segment-count"),
    cachePill: document.querySelector("#cache-pill"),
    segments: document.querySelector("#segments"),
    transcriptSearch: document.querySelector("#transcript-search"),
    searchCount: document.querySelector("#search-count"),
    timestampsToggle: document.querySelector("#timestamps-toggle"),
    copyButton: document.querySelector("#copy-button"),
    trackLanguage: document.querySelector("#track-language"),
    downloadButton: document.querySelector("#download-button"),
    downloadOptions: document.querySelector("#download-options"),
    history: document.querySelector("#history"),
    historyItems: document.querySelector("#history-items"),
  };

  const HISTORY_KEY = "tubetext-history-v1";
  const params = new URLSearchParams(window.location.search);
  const isEmbed = window.location.pathname === "/embed" || params.get("embed") === "1";
  document.body.classList.toggle("embed-mode", isEmbed);

  function notifyParentHeight() {
    if (window.parent === window) return;
    const height = Math.ceil(document.documentElement.scrollHeight);
    window.parent.postMessage({ type: "tubetext:resize", height }, "*");
  }

  const resizeObserver = new ResizeObserver(() => notifyParentHeight());
  resizeObserver.observe(document.documentElement);

  function setLoading(isLoading) {
    elements.form.classList.toggle("loading", isLoading);
    elements.generateButton.disabled = isLoading;
    elements.url.disabled = isLoading;
    elements.preferredLanguage.disabled = isLoading;
    elements.generateButton.querySelector(".button-label").textContent = isLoading ? "Hämtar..." : "Hämta text";
  }

  function showMessage(text, type = "error") {
    elements.message.textContent = text;
    elements.message.className = `message ${type === "success" ? "success" : ""}`;
    elements.message.hidden = false;
  }

  function hideMessage() {
    elements.message.hidden = true;
  }

  async function requestTranscript({ url, languageCode = null }) {
    const preferredValue = elements.preferredLanguage.value;
    const preferredLanguages = preferredValue === "auto" ? [] : preferredValue.split(",");

    const response = await fetch("/api/transcripts", {
      method: "POST",
      headers: { "Content-Type": "application/json", Accept: "application/json" },
      body: JSON.stringify({
        url,
        preferred_languages: preferredLanguages.length ? preferredLanguages : ["sv", "en"],
        language_code: languageCode,
      }),
    });

    let payload;
    try {
      payload = await response.json();
    } catch {
      throw new Error("Servern svarade inte med giltig data.");
    }

    if (!response.ok) {
      throw new Error(payload.error || payload.detail?.error || "Det gick inte att hämta transkriptionen.");
    }
    return payload;
  }

  async function generate(url, languageCode = null) {
    hideMessage();
    setLoading(true);
    try {
      const data = await requestTranscript({ url, languageCode });
      state.data = data;
      state.url = url;
      state.query = "";
      elements.transcriptSearch.value = "";
      renderResult();
      saveHistory({ url, title: data.video.title || `YouTube ${data.video.video_id}` });
    } catch (error) {
      showMessage(error instanceof Error ? error.message : "Ett oväntat fel inträffade.");
    } finally {
      setLoading(false);
    }
  }

  function renderResult() {
    const { data } = state;
    if (!data) return;

    elements.result.hidden = false;
    elements.player.src = `${data.video.embed_url}?rel=0`;
    elements.videoTitle.textContent = data.video.title || "YouTube-video";
    elements.videoAuthor.textContent = data.video.author_name || "YouTube";
    elements.languagePill.textContent = `${data.language}${data.is_generated ? " · automatisk" : " · manuell"}`;
    elements.segmentCount.textContent = `${data.segments.length} segment`;
    elements.cachePill.hidden = !data.cached;
    renderLanguageOptions();
    renderSegments();
    if (!isEmbed) elements.result.scrollIntoView({ behavior: "smooth", block: "start" });
    notifyParentHeight();
  }

  function renderLanguageOptions() {
    const { data } = state;
    elements.trackLanguage.replaceChildren();
    const sorted = [...data.available_languages].sort((a, b) => a.language.localeCompare(b.language, "sv"));
    for (const track of sorted) {
      const option = document.createElement("option");
      option.value = track.language_code;
      option.textContent = `${track.language}${track.is_generated ? " (auto)" : ""}`;
      option.selected = track.language_code === data.language_code;
      elements.trackLanguage.append(option);
    }
  }

  function renderSegments() {
    const { data, query } = state;
    if (!data) return;

    const normalizedQuery = query.trim().toLocaleLowerCase("sv");
    const matching = normalizedQuery
      ? data.segments.filter((segment) => segment.text.toLocaleLowerCase("sv").includes(normalizedQuery))
      : data.segments;

    elements.segments.replaceChildren();
    elements.segments.classList.toggle("no-timestamps", !elements.timestampsToggle.checked);
    elements.searchCount.textContent = normalizedQuery ? `${matching.length} träffar` : "";

    if (!matching.length) {
      const empty = document.createElement("div");
      empty.className = "empty-search";
      empty.textContent = "Ingen text matchade sökningen.";
      elements.segments.append(empty);
      return;
    }

    const fragment = document.createDocumentFragment();
    for (const segment of matching) {
      const row = document.createElement("article");
      row.className = "segment";

      const timeButton = document.createElement("button");
      timeButton.className = "segment-time";
      timeButton.type = "button";
      timeButton.textContent = formatClock(segment.start);
      timeButton.title = `Spela från ${formatClock(segment.start)}`;
      timeButton.addEventListener("click", () => seekTo(segment.start));

      const text = document.createElement("p");
      text.className = "segment-text";
      appendHighlightedText(text, segment.text, query.trim());

      row.append(timeButton, text);
      fragment.append(row);
    }
    elements.segments.append(fragment);
  }

  function appendHighlightedText(container, text, query) {
    if (!query) {
      container.textContent = text;
      return;
    }
    const lower = text.toLocaleLowerCase("sv");
    const needle = query.toLocaleLowerCase("sv");
    let cursor = 0;
    let index = lower.indexOf(needle);
    while (index !== -1) {
      container.append(document.createTextNode(text.slice(cursor, index)));
      const mark = document.createElement("mark");
      mark.textContent = text.slice(index, index + query.length);
      container.append(mark);
      cursor = index + query.length;
      index = lower.indexOf(needle, cursor);
    }
    container.append(document.createTextNode(text.slice(cursor)));
  }

  function seekTo(seconds) {
    if (!state.data) return;
    const start = Math.max(0, Math.floor(seconds));
    elements.player.src = `${state.data.video.embed_url}?start=${start}&autoplay=1&rel=0`;
  }

  function formatClock(seconds) {
    const total = Math.max(0, Math.floor(seconds));
    const hours = Math.floor(total / 3600);
    const minutes = Math.floor((total % 3600) / 60);
    const secs = total % 60;
    return hours > 0
      ? `${hours}:${String(minutes).padStart(2, "0")}:${String(secs).padStart(2, "0")}`
      : `${minutes}:${String(secs).padStart(2, "0")}`;
  }

  function formatSubtitleTime(seconds, separator = ",") {
    const totalMs = Math.max(0, Math.round(seconds * 1000));
    const hours = Math.floor(totalMs / 3_600_000);
    const minutes = Math.floor((totalMs % 3_600_000) / 60_000);
    const secs = Math.floor((totalMs % 60_000) / 1000);
    const ms = totalMs % 1000;
    return `${String(hours).padStart(2, "0")}:${String(minutes).padStart(2, "0")}:${String(secs).padStart(2, "0")}${separator}${String(ms).padStart(3, "0")}`;
  }

  function exportContent(format) {
    const { data } = state;
    if (!data) return;
    if (format === "txt") return data.segments.map((s) => `[${formatClock(s.start)}] ${s.text}`).join("\n");
    if (format === "srt") {
      return data.segments.map((s, i) => {
        const end = s.start + Math.max(s.duration, 0.4);
        return `${i + 1}\n${formatSubtitleTime(s.start)} --> ${formatSubtitleTime(end)}\n${s.text}`;
      }).join("\n\n");
    }
    return `WEBVTT\n\n${data.segments.map((s) => {
      const end = s.start + Math.max(s.duration, 0.4);
      return `${formatSubtitleTime(s.start, ".")} --> ${formatSubtitleTime(end, ".")}\n${s.text}`;
    }).join("\n\n")}`;
  }

  function download(format) {
    if (!state.data) return;
    const content = exportContent(format);
    const mime = format === "txt" ? "text/plain" : "text/vtt";
    const blob = new Blob([content], { type: `${mime};charset=utf-8` });
    const link = document.createElement("a");
    link.href = URL.createObjectURL(blob);
    link.download = `${slugify(state.data.video.title || state.data.video.video_id)}.${format}`;
    document.body.append(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(link.href);
    elements.downloadOptions.hidden = true;
    elements.downloadButton.setAttribute("aria-expanded", "false");
  }

  function slugify(value) {
    return value
      .normalize("NFKD")
      .replace(/[\u0300-\u036f]/g, "")
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, "-")
      .replace(/^-|-$/g, "")
      .slice(0, 80) || "youtube-transcript";
  }

  async function copyTranscript() {
    if (!state.data) return;
    const text = exportContent("txt");
    try {
      await navigator.clipboard.writeText(text);
      const original = elements.copyButton.textContent;
      elements.copyButton.textContent = "Kopierat";
      setTimeout(() => { elements.copyButton.textContent = original; }, 1400);
    } catch {
      showMessage("Webbläsaren kunde inte kopiera automatiskt. Ladda ner TXT-filen i stället.");
    }
  }

  function getHistory() {
    try {
      const parsed = JSON.parse(localStorage.getItem(HISTORY_KEY) || "[]");
      return Array.isArray(parsed) ? parsed : [];
    } catch {
      return [];
    }
  }

  function saveHistory(item) {
    const history = getHistory().filter((existing) => existing.url !== item.url);
    history.unshift(item);
    localStorage.setItem(HISTORY_KEY, JSON.stringify(history.slice(0, 5)));
    renderHistory();
  }

  function renderHistory() {
    const history = getHistory();
    elements.history.hidden = history.length === 0;
    elements.historyItems.replaceChildren();
    for (const item of history) {
      const button = document.createElement("button");
      button.type = "button";
      button.className = "history-item";
      button.textContent = item.title;
      button.title = item.title;
      button.addEventListener("click", () => {
        elements.url.value = item.url;
        generate(item.url);
      });
      elements.historyItems.append(button);
    }
  }

  elements.form.addEventListener("submit", (event) => {
    event.preventDefault();
    const url = elements.url.value.trim();
    if (!url) {
      showMessage("Klistra in en YouTube-länk först.");
      elements.url.focus();
      return;
    }
    generate(url);
  });

  elements.transcriptSearch.addEventListener("input", () => {
    state.query = elements.transcriptSearch.value;
    renderSegments();
  });

  elements.timestampsToggle.addEventListener("change", renderSegments);
  elements.copyButton.addEventListener("click", copyTranscript);

  elements.trackLanguage.addEventListener("change", () => {
    if (state.url) generate(state.url, elements.trackLanguage.value);
  });

  elements.downloadButton.addEventListener("click", () => {
    const willOpen = elements.downloadOptions.hidden;
    elements.downloadOptions.hidden = !willOpen;
    elements.downloadButton.setAttribute("aria-expanded", String(willOpen));
  });

  elements.downloadOptions.addEventListener("click", (event) => {
    const button = event.target.closest("button[data-format]");
    if (button) download(button.dataset.format);
  });

  document.addEventListener("click", (event) => {
    if (!event.target.closest(".download-menu")) {
      elements.downloadOptions.hidden = true;
      elements.downloadButton.setAttribute("aria-expanded", "false");
    }
  });

  renderHistory();
  const initialUrl = params.get("url");
  if (initialUrl) {
    elements.url.value = initialUrl;
    generate(initialUrl);
  }
  notifyParentHeight();
})();
