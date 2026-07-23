(() => {
  "use strict";

  const scriptUrl = new URL(document.currentScript?.src || window.location.href);
  const appOrigin = scriptUrl.origin;

  class TubeTextWidget extends HTMLElement {
    connectedCallback() {
      if (this.shadowRoot) return;

      const shadow = this.attachShadow({ mode: "open" });
      const iframe = document.createElement("iframe");
      const initialUrl = this.getAttribute("video-url") || "";
      const src = new URL("/embed", appOrigin);
      if (initialUrl) src.searchParams.set("url", initialUrl);

      iframe.src = src.toString();
      iframe.title = this.getAttribute("title") || "YouTube-transkribering";
      iframe.loading = "lazy";
      iframe.allow = "clipboard-write; fullscreen";
      iframe.referrerPolicy = "strict-origin-when-cross-origin";
      iframe.style.cssText = [
        "display:block",
        "width:100%",
        `height:${this.getAttribute("height") || "760px"}`,
        "border:0",
        `border-radius:${this.getAttribute("radius") || "18px"}`,
        "background:#0b0d12",
      ].join(";");

      shadow.append(iframe);
      this._iframe = iframe;
      this._onMessage = (event) => {
        if (event.origin !== appOrigin || event.source !== iframe.contentWindow) return;
        if (event.data?.type !== "tubetext:resize") return;
        const height = Math.max(520, Math.min(Number(event.data.height) || 760, 1400));
        iframe.style.height = `${height}px`;
      };
      window.addEventListener("message", this._onMessage);
    }

    disconnectedCallback() {
      if (this._onMessage) window.removeEventListener("message", this._onMessage);
    }
  }

  if (!customElements.get("tubetext-widget")) {
    customElements.define("tubetext-widget", TubeTextWidget);
  }
})();
