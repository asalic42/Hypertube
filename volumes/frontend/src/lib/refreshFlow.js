import { ensureCsrfToken } from './csrf';

export async function refreshAccessToken() {
    const csrfToken = await ensureCsrfToken();
    const response = await fetch('https://localhost:8080/api/auth/refresh/', {
    method: 'POST',
    headers: {
      'X-CSRFToken': csrfToken,
    },
    credentials: 'include',
    });

    if (!response.ok) {
    throw new Error('Impossible de rafraîchir la session');
    }
    const data = await response.json();
    localStorage.setItem('access_token', data.access);
    return data.access;
}


export async function fetchWithAuth(url, options = {}) {
    let accessToken = localStorage.getItem('access_token');

    let response = await fetch(url, {
    ...options,
    headers: {
        ...options.headers,
        Authorization: `Bearer ${accessToken}`,
    },
    credentials: 'include',
    });

    if (response.status === 401) {
        try {
            accessToken = await refreshAccessToken();
            
            response = await fetch(url, {
            ...options,
            headers: {
                ...options.headers,
                Authorization: `Bearer ${accessToken}`,
            },
            credentials: 'include',
            });
        } catch (err) {
            localStorage.removeItem('access_token');
            throw err;
        }
    }

    return response;
}