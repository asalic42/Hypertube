// The password rules the auth service enforces (Django's validators), checked
// here first so that an obviously refused password never leaves the browser:
// no request, no 400 in the console. The server stays the judge: it also knows
// the list of common passwords, which is too long to ship.

export const PASSWORD_MIN_LENGTH = 8;

// A short list of the passwords everyone tries; the server knows thousands more.
const COMMON = new Set([
  "password", "password1", "passw0rd", "12345678", "123456789", "1234567890",
  "qwerty123", "qwertyuiop", "iloveyou", "sunshine", "princess", "football",
  "baseball", "welcome", "abc12345", "letmein", "monkey123", "dragon123",
  "azertyuiop", "motdepasse", "contraseña",
]);

/**
 * The reason a password would be refused, as a sentence to translate, or null
 * when nothing visible from here is wrong with it.
 * `account` carries the username and email it must not resemble.
 */
export function passwordProblem(password, account = {}) {
  if (password.length < PASSWORD_MIN_LENGTH) {
    return "This password is too short. It must contain at least {count} characters.";
  }
  if (/^\d+$/.test(password)) {
    return "This password is entirely numeric.";
  }
  if (COMMON.has(password.toLowerCase())) {
    return "This password is too common.";
  }
  const lowered = password.toLowerCase();
  const parts = [account.username, account.email, account.email?.split("@")[0]]
    .map((value) => String(value || "").trim().toLowerCase())
    .filter((value) => value.length >= 3);
  if (parts.some((value) => lowered.includes(value) || value.includes(lowered))) {
    return "This password is too similar to your username or email.";
  }
  return null;
}

export const PASSWORD_PROBLEM_PARAMS = { count: PASSWORD_MIN_LENGTH };
