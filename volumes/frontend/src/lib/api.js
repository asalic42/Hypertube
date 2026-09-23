// Same-origin calls through the nginx proxy: the access token lives in memory
// and is renewed from the httpOnly refresh cookie when it expires.

let accessToken = null;
let refreshing = null;

export class ApiError extends Error {
  constructor(status, data) {
    super(data?.detail || firstFieldError(data) || `Request failed (${status})`);
    this.status = status;
    this.data = data;
  }
}

function firstFieldError(data) {
  if (!data || typeof data !== 'object') return null;
  const [field, messages] = Object.entries(data)[0] || [];
  if (!field) return null;
  const message = Array.isArray(messages) ? messages[0] : messages;
  return field === 'non_field_errors' ? String(message) : `${field}: ${message}`;
}

function getCookie(name) {
  const match = document.cookie.match(new RegExp(`(?:^|; )${name}=([^;]*)`));
  return match ? decodeURIComponent(match[1]) : null;
}

async function csrfToken() {
  if (!getCookie('csrftoken')) {
    await fetch('/api/auth/csrf/', { credentials: 'include' });
  }
  return getCookie('csrftoken');
}

async function parse(response) {
  if (response.status === 204) return null;
  const text = await response.text();
  try {
    return text ? JSON.parse(text) : null;
  } catch {
    return { detail: text };
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
  // Concurrent 401s share one refresh call.
  refreshing ??= (async () => {
    try {
      const response = await rawFetch('/api/auth/refresh/', { method: 'POST', auth: false, csrf: true });
      if (!response.ok) return null;
      const data = await parse(response);
      accessToken = data?.access || null;
      return accessToken;
    } finally {
      refreshing = null;
    }
  })();
  return refreshing;
}

export async function api(path, options = {}) {
  let response = await rawFetch(path, options);
  if (response.status === 401 && options.auth !== false && (await refreshAccessToken())) {
    response = await rawFetch(path, options);
  }
  const data = await parse(response);
  if (!response.ok) throw new ApiError(response.status, data);
  return data;
}

export function setAccessToken(token) {
  accessToken = token;
}

export function hasAccessToken() {
  return Boolean(accessToken);
}

export const auth = {
  async login(email, password) {
    const data = await api('/api/auth/login/', { method: 'POST', body: { email, password }, auth: false, csrf: true });
    accessToken = data.access;
    return data.user;
  },
  async logout() {
    try {
      await api('/api/auth/logout/', { method: 'POST', csrf: true });
    } finally {
      accessToken = null;
    }
  },
  me() {
    return api('/api/auth/me/');
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

export const comments = {
  update(id, comment) {
    return api(`/api/comments/${id}/`, { method: 'PATCH', body: { comment } });
  },
  remove(id) {
    return api(`/api/comments/${id}/`, { method: 'DELETE' });
  },
};
