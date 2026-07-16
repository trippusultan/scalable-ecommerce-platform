// Inline SVG line-art of the ACTUAL product for each card.
// Drawn in the same ink line-style + matte tint as the rest of the design,
// so every image shares the same contrast and the grid reads as one cohesive set.
// Keyed by product name keywords so it stays correct regardless of DB id.

const INK = "#1F1D1A";

function svg(inner) {
  return (
    `<svg class="thumb-svg" viewBox="0 0 100 75" preserveAspectRatio="xMidYMid meet" ` +
    `role="img" xmlns="http://www.w3.org/2000/svg">` +
    `<g fill="none" stroke="${INK}" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">` +
    inner +
    `</g></svg>`
  );
}

const MOUSE = svg(`
  <rect x="38" y="20" width="24" height="38" rx="12" />
  <line x1="50" y1="20" x2="50" y2="40" />
  <line x1="38" y1="30" x2="32" y2="34" />
  <line x1="62" y1="30" x2="68" y2="34" />
  <line x1="50" y1="55" x2="50" y2="58" />
`);

const KEYBOARD = svg(`
  <rect x="20" y="28" width="60" height="26" rx="5" />
  <line x1="28" y1="36" x2="40" y2="36" />
  <line x1="44" y1="36" x2="56" y2="36" />
  <line x1="60" y1="36" x2="72" y2="36" />
  <line x1="28" y1="44" x2="40" y2="44" />
  <line x1="44" y1="44" x2="56" y2="44" />
  <line x1="60" y1="44" x2="72" y2="44" />
  <line x1="34" y1="28" x2="34" y2="22" />
  <line x1="50" y1="28" x2="50" y2="22" />
  <line x1="66" y1="28" x2="66" y2="22" />
`);

const HUB = svg(`
  <rect x="26" y="30" width="48" height="16" rx="4" />
  <line x1="34" y1="30" x2="34" y2="24" />
  <line x1="46" y1="30" x2="46" y2="24" />
  <line x1="58" y1="30" x2="58" y2="24" />
  <line x1="66" y1="30" x2="66" y2="24" />
  <rect x="40" y="46" width="20" height="6" rx="2" />
  <line x1="50" y1="24" x2="50" y2="20" />
`);

const BOOK = svg(`
  <path d="M50 22 C40 18 28 18 22 22 L22 54 C28 50 40 50 50 54 C60 50 72 50 78 54 L78 22 C72 18 60 18 50 22 Z" />
  <line x1="50" y1="22" x2="50" y2="54" />
`);

const MUG = svg(`
  <path d="M34 26 L34 52 C34 56 38 58 44 58 L52 58 C58 58 62 56 62 52 L62 26 Z" />
  <path d="M62 32 C72 32 74 44 62 46" />
  <line x1="34" y1="34" x2="62" y2="34" />
`);

const BOTTLE = svg(`
  <path d="M44 20 L44 26 L40 32 L40 54 C40 57 43 58 50 58 C57 58 60 57 60 54 L60 32 L56 26 L56 20 Z" />
  <line x1="40" y1="40" x2="60" y2="40" />
`);

const BLOCKS = svg(`
  <rect x="26" y="40" width="14" height="14" rx="2" />
  <rect x="42" y="34" width="14" height="14" rx="2" />
  <rect x="58" y="44" width="14" height="14" rx="2" />
  <rect x="36" y="26" width="12" height="12" rx="2" />
`);

const GENERIC = svg(`
  <rect x="34" y="26" width="32" height="32" rx="6" />
  <line x1="34" y1="42" x2="66" y2="42" />
  <circle cx="50" cy="42" r="3" />
`);

function pick(name) {
  const n = (name || "").toLowerCase();
  if (n.includes("mouse")) return MOUSE;
  if (n.includes("keyboard")) return KEYBOARD;
  if (n.includes("hub")) return HUB;
  if (n.includes("mug")) return MUG;
  if (n.includes("bottle")) return BOTTLE;
  if (n.includes("block")) return BLOCKS;
  if (n.includes("code") || n.includes("pragmatic") || n.includes("book")) return BOOK;
  return GENERIC;
}

// Real product photos (verified Unsplash CDN URLs). Used as the primary
// image; ProductImage falls back to the line-art SVG if a photo fails to load.
const PHOTOS = {
  mouse: "https://images.unsplash.com/photo-1527864550417-7fd91fc51a46?w=800&q=80",
  keyboard: "https://images.unsplash.com/photo-1587829741301-dc798b83add3?w=800&q=80",
  hub: "https://images.unsplash.com/photo-1595225476474-87563907a212?w=800&q=80",
  book_cleancode: "https://images.unsplash.com/photo-1544947950-fa07a98d237f?w=800&q=80",
  book_pragmatic: "https://images.unsplash.com/photo-1532012197267-da84d127e765?w=800&q=80",
  mug: "https://images.unsplash.com/photo-1514228742587-6b1558fcca3d?w=800&q=80",
  bottle: "https://images.unsplash.com/photo-1602143407151-7111542de6e8?w=800&q=80",
  blocks: "https://images.unsplash.com/photo-1535378917042-10a22c95931a?w=800&q=80",
};

function pickPhoto(name) {
  const n = (name || "").toLowerCase();
  if (n.includes("mouse")) return PHOTOS.mouse;
  if (n.includes("keyboard")) return PHOTOS.keyboard;
  if (n.includes("hub")) return PHOTOS.hub;
  if (n.includes("mug")) return PHOTOS.mug;
  if (n.includes("bottle")) return PHOTOS.bottle;
  if (n.includes("block")) return PHOTOS.blocks;
  if (n.includes("clean code")) return PHOTOS.book_cleancode;
  if (n.includes("pragmatic")) return PHOTOS.book_pragmatic;
  if (n.includes("code") || n.includes("book")) return PHOTOS.book_cleancode;
  return null;
}

export function productImage(product) {
  return pick(product && product.name);
}

export function productImageUrl(product) {
  return pickPhoto(product && product.name);
}
