export const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1';

// --> JWT helpers
export function getToken() {
  return localStorage.getItem('cp_token');
}
export function setToken(token) {
  localStorage.setItem('cp_token', token);
  localStorage.setItem('cp_session', '1'); // remember this browser logged in once
}
export function clearToken() {
  localStorage.removeItem('cp_token');
  localStorage.removeItem('cp_session');
}

function authHeaders(extra = {}) {
  const token = getToken();
  return token ? { Authorization: `Bearer ${token}`, ...extra } : { ...extra };
}

// --> Silent refresh: swap the httpOnly cookie for a fresh access token
let refreshingPromise = null;
export async function tryRefresh() {
  if (refreshingPromise) return refreshingPromise;
  refreshingPromise = (async () => {
    try {
      const r = await fetch(`${API_BASE_URL}/auth/refresh`, {
        method: 'POST',
        credentials: 'include', // send the cp_refresh cookie
      });
      if (!r.ok) return null;
      const data = await r.json();
      setToken(data.access_token);
      return data.access_token;
    } catch {
      return null;
    } finally {
      refreshingPromise = null;
    }
  })();
  return refreshingPromise;
}

// fetch wrapper: attaches token, retries once after silent refresh on 401
async function authedFetch(url, options = {}) {
  let response = await fetch(url, { ...options, headers: authHeaders(options.headers || {}) });
  if (response.status === 401) {
    const fresh = await tryRefresh();
    if (fresh) {
      response = await fetch(url, { ...options, headers: authHeaders(options.headers || {}) });
    }
  }
  return response;
}

function parseError(response) {
  return response.json().catch(() => ({})).then((data) => {
    if (response.status === 401) clearToken();
    return new Error(data.detail || data.error || `Server error: ${response.status}`);
  });
}

// --> Submit code for analysis
export async function submitCodeAnalysis(title, code, language) {
  const response = await authedFetch(`${API_BASE_URL}/analyze`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ title, code, language }),
  });

  if (!response.ok) throw await parseError(response);
  return response.json();
}

// --> Get job status
export async function getJobStatus(jobId) {
  const response = await authedFetch(`${API_BASE_URL}/jobs/${jobId}`);

  if (!response.ok) throw await parseError(response);
  return response.json();
}

// --> Submit a repository (GitHub URL or .zip upload) for analysis
export async function submitRepoAnalysis(githubUrl, file) {
  const form = new FormData();
  if (githubUrl) form.append('github_url', githubUrl);
  else if (file) form.append('file', file);
  else throw new Error('Provide a GitHub URL or a .zip file.');

  const response = await authedFetch(`${API_BASE_URL}/analyze-repo`, {
    method: 'POST',
    body: form, // browser sets multipart boundary automatically
  });

  if (!response.ok) throw await parseError(response);
  return response.json();
}

// --> Fetch the signed-in user's profile
export async function fetchMe() {
  const response = await authedFetch(`${API_BASE_URL}/auth/me`);
  if (!response.ok) {
    if (response.status === 401) clearToken();
    return null;
  }
  return response.json();
}

// --> Sign out server-side (clears the httpOnly cookie)
export async function logoutServer() {
  await fetch(`${API_BASE_URL}/auth/logout`, {
    method: 'POST',
    credentials: 'include',
  }).catch(() => {});
}
