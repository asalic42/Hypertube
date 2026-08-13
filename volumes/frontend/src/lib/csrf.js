import { getCookie } from './cookies';

export async function ensureCsrfToken() {
  let csrfToken = getCookie('csrftoken');
  if (!csrfToken) {
    await fetch('https://localhost:8080/api/csrf/', { credentials: 'include' });
    csrfToken = getCookie('csrftoken');
  }
  return csrfToken;
}
