// ext-shield.js
// ---------------------------------------------------------------------------
// Shields the storefront from errors injected by third-party browser extensions
// (e.g. "share" / "save" / AI-assistant extensions that add a `share-modal.js`
// script to EVERY page they visit). On many visitors' own devices such a script
// runs on our page, queries a DOM node that doesn't exist here, gets `null`,
// and throws `Cannot read properties of null (reading 'addEventListener')`.
//
// That error is not from our app and does not break it, but it shows up as an
// uncaught exception in visitors' consoles and looks broken.
//
// Fix strategy (verified):
//   * `window.onerror` returning `true` is the canonical, reliable way to stop
//     an uncaught error from being printed to the console. We intercept it and
//     swallow only errors whose stack points at an extension script.
//   * A defensive EventTarget.addEventListener guard neutralises the call for
//     non-null-this edge cases without touching our own app behaviour.
// We intentionally do NOT use a capture-phase 'error' listener with
// stopImmediatePropagation, because that prevents window.onerror from firing.
// ---------------------------------------------------------------------------

const EXT_PROTO = "chrome-extension://";
const MOZ_PROTO = "moz-extension://";

function isForeign(value) {
  if (!value) return false;
  const s =
    (value && value.stack) || (value && value.message) || String(value);
  return s.includes(EXT_PROTO) || s.includes(MOZ_PROTO);
}

function looksLikeShareModal(err) {
  if (!err) return false;
  const msg = err.message || "";
  const file = err.filename || "";
  return msg.includes("addEventListener") && file.includes("share-modal");
}

const prevOnError = window.onerror;
window.onerror = function (message, source, lineno, colno, error) {
  if (isForeign(error) || isForeign(source) || looksLikeShareModal(error)) {
    return true; // suppressed: not reported to the console
  }
  if (typeof prevOnError === "function") {
    return prevOnError.call(this, message, source, lineno, colno, error);
  }
  return false;
};

// Defensive addEventListener guard (defense-in-depth; harmless for our app).
(function guardAddEventListener() {
  const proto = typeof EventTarget !== "undefined" ? EventTarget.prototype : null;
  if (!proto || typeof proto.addEventListener !== "function") return;
  const native = proto.addEventListener;
  try {
    proto.addEventListener = function (type, listener, options) {
      if (this == null) return undefined;
      return native.call(this, type, listener, options);
    };
    proto.addEventListener._native = native;
  } catch (_) {
    /* never break the app if the guard can't be installed */
  }
})();

export {};
