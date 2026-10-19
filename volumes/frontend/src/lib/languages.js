// Same codes as PublicUser.LANGUAGE_CHOICES in the users service.
export const LANGUAGES = [
  ["en", "English"],
  ["fr", "French"],
  ["es", "Spanish"],
  ["de", "German"],
  ["it", "Italian"],
  ["pt", "Portuguese"],
  ["ru", "Russian"],
  ["zh", "Chinese"],
  ["ja", "Japanese"],
  ["ko", "Korean"],
];

// The browser's language when it is one we support, English otherwise.
export function defaultLanguage() {
  const code = (navigator.language || "").slice(0, 2).toLowerCase();
  return LANGUAGES.some(([value]) => value === code) ? code : "en";
}
