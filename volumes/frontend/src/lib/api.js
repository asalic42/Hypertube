
let accessToken = null;
// Expiry of the access token (ms since epoch), read from its payload.
let accessExpiry = 0;
let refreshing = null;
// Refresh this long before the access token expires, so no request ever gets a 401.
const EXPIRY_MARGIN = 30 * 1000;
// Set by the auth service next to the httpOnly refresh cookie: when it is
// absent there is no session, and asking for a refresh would only log a 401.
const SESSION_MARKER = 'logged_in';

export class ApiError extends Error {
  constructor(status, data) {
    super(data?.detail || fieldErrors(data) || `Request failed (${status})`);
    this.status = status;
    this.data = data;
  }
}

// Labels for the fields named in validation errors, so a message reads as a sentence.
const FIELD_LABELS = {
  username: 'Username',
  email: 'Email',
  password: 'Password',
  password_confirmation: 'Password confirmation',
  new_password: 'New password',
  confirm_password: 'Password confirmation',
  firstname: 'First name',
  lastname: 'Last name',
  avatar: 'Picture',
  preferredLanguage: 'Language',
  comment: 'Comment',
  quality: 'Quality',
  language: 'Language',
};

// Every field error of a validation answer, in one readable sentence.
function fieldErrors(data) {
  if (!data || typeof data !== 'object') return null;
  const parts = Object.entries(data).map(([field, messages]) => {
    const message = Array.isArray(messages) ? messages.join(' ') : String(messages);
    return field === 'non_field_errors' ? message : `${FIELD_LABELS[field] || field}: ${message}`;
  });
  return parts.length ? parts.join(' ') : null;
}

function getCookie(name) {
  const match = document.cookie.match(new RegExp(`(?:^|; )${name}=([^;]*)`));
  return match ? decodeURIComponent(match[1]) : null;
}

function setToken(token) {
  accessToken = token || null;
  accessExpiry = 0;
  if (!token) return;
  try {
    const payload = JSON.parse(atob(token.split('.')[1].replace(/-/g, '+').replace(/_/g, '/')));
    if (payload.exp) accessExpiry = payload.exp * 1000;
  } catch {
    // Not a JWT we can read: it will be refreshed on the first 401 instead.
  }
}

function tokenIsFresh() {
  return Boolean(accessToken) && (accessExpiry === 0 || accessExpiry - Date.now() > EXPIRY_MARGIN);
}

export function hasSession() {
  return getCookie(SESSION_MARKER) === '1';
}

async function csrfToken() {
  if (!getCookie('csrftoken')) {
    await fetch('/api/auth/csrf/', { credentials: 'include' });
  }
  return getCookie('csrftoken');
}

const STATUS_MESSAGES = {
  413: 'The file is too large.',
  429: 'Too many requests, please wait a moment.',
  502: 'The server is unavailable right now.',
  503: 'The server is unavailable right now.',
  504: 'The server took too long to answer.',
};

async function parse(response) {
  if (response.status === 204) return null;
  const text = await response.text();
  try {
    return text ? JSON.parse(text) : null;
  } catch {
    return { detail: STATUS_MESSAGES[response.status] || `Request failed (${response.status})` };
  }
}

async function rawFetch(path, { method = 'GET', body, headers = {}, auth = true, csrf = false } = {}) {
  const options = { method, headers: { Accept: 'application/json', ...headers }, credentials: 'include' };
  if (body instanceof FormData) {
    options.body = body;
  } else if (body !== undefined) {
    options.headers['Content-Type'] = 'application/json';
    options.body = JSON.stringify(body);
  }
  if (auth && accessToken) options.headers.Authorization = `Bearer ${accessToken}`;
  if (csrf) options.headers['X-CSRFToken'] = await csrfToken();
  return fetch(path, options);
}

export async function refreshAccessToken() {
  // No session: nothing to refresh, and no request that the browser would log as failed.
  if (!hasSession()) {
    setToken(null);
    return null;
  }
  // Concurrent callers share one refresh call.
  refreshing ??= (async () => {
    try {
      const response = await rawFetch('/api/auth/refresh/', { method: 'POST', auth: false, csrf: true });
      if (!response.ok) {
        setToken(null);
        return null;
      }
      const data = await parse(response);
      setToken(data?.access);
      return accessToken;
    } finally {
      refreshing = null;
    }
  })();
  return refreshing;
}

export async function api(path, options = {}) {
  // Renew an expiring token before using it, rather than after a 401.
  if (options.auth !== false && !tokenIsFresh() && hasSession()) await refreshAccessToken();
  let response = await rawFetch(path, options);
  if (response.status === 401 && options.auth !== false && (await refreshAccessToken())) {
    response = await rawFetch(path, options);
  }
  const data = await parse(response);
  if (!response.ok) throw new ApiError(response.status, data);
  return data;
}

export function setAccessToken(token) {
  setToken(token);
}

export function hasAccessToken() {
  return Boolean(accessToken);
}

export const auth = {
  async login(email, password) {
    const data = await api('/api/auth/login/', { method: 'POST', body: { email, password }, auth: false, csrf: true });
    setToken(data.access);
    return data.user;
  },
  async logout() {
    try {
      await api('/api/auth/logout/', { method: 'POST', csrf: true });
    } finally {
      setToken(null);
    }
  },
  me() {
    return api('/api/auth/me/');
  },
  updateMe(fields) {
    return api('/api/auth/me/', { method: 'PATCH', body: fields, csrf: true });
  },
  deleteMe() {
    return api('/api/auth/me/', { method: 'DELETE', csrf: true });
  },
};

export const movies = {
  list(params) {
    const query = new URLSearchParams();
    for (const [key, value] of Object.entries(params)) {
      if (value !== '' && value !== undefined && value !== null) query.set(key, value);
    }
    return api(`/api/movies/?${query}`);
  },
  get(id) {
    return api(`/api/movies/${id}/`);
  },
  genres() {
    return api('/api/movies/genres/');
  },
  download(id) {
    return api(`/api/movies/${id}/download/`);
  },
  requestDownload(id) {
    return api(`/api/movies/${id}/download/`, { method: 'PUT', body: {} });
  },
  comments(id, page = 1) {
    return api(`/api/movies/${id}/comments/?page=${page}`);
  },
  addComment(id, comment) {
    return api(`/api/movies/${id}/comments/`, { method: 'POST', body: { comment } });
  },
};

export const users = {
  async get(username) {
    const data = await api(`/api/users/${encodeURIComponent(username)}/`);
    return data.user;
  },
  async avatarUrl(username) {
    try {
      const data = await api(`/api/users/${encodeURIComponent(username)}/avatar/`);
      return data.avatar_url;
    } catch (err) {
      if (err instanceof ApiError && err.status === 404) return null;
      throw err;
    }
  },
  async update(username, fields) {
    const body = new FormData();
    for (const [key, value] of Object.entries(fields)) body.append(key, value);
    const data = await api(`/api/users/${encodeURIComponent(username)}/`, { method: 'PATCH', body });
    return data.user;
  },
  updateAvatar(username, file) {
    const body = new FormData();
    body.append('avatar', file);
    return api(`/api/users/${encodeURIComponent(username)}/avatar/`, { method: 'PATCH', body });
  },
  deleteAvatar(username) {
    return api(`/api/users/${encodeURIComponent(username)}/avatar/`, { method: 'DELETE' });
  },
  remove(username) {
    return api(`/api/users/${encodeURIComponent(username)}/`, { method: 'DELETE' });
  },
};

export const comments = {
  update(id, comment) {
    return api(`/api/comments/${id}/`, { method: 'PATCH', body: { comment } });
  },
  remove(id) {
    return api(`/api/comments/${id}/`, { method: 'DELETE' });
  },
};
