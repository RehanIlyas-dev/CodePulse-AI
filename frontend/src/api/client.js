export const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1';

// --> JWT helpers
export function getToken() {
  return localStorage.getItem('cp_token');
}
export function setToken(token) {
  localStorage.setItem('cp_token', token);
}
export function clearToken() {
  localStorage.removeItem('cp_token');
}

function authHeaders(extra = {}) {
  const token = getToken();
  return token ? { Authorization: `Bearer ${token}`, ...extra } : { ...extra };
}

async function parseError(response) {
  const data = await response.json().catch(() => ({}));
  if (response.status === 401) clearToken();
  return new Error(data.detail || data.error || `Server error: ${response.status}`);
}

// --> Submit code for analysis
export async function submitCodeAnalysis(title, code, language) {
  const response = await fetch(`${API_BASE_URL}/analyze`, {
    method: 'POST',
    headers: authHeaders({ 'Content-Type': 'application/json' }),
    body: JSON.stringify({ title, code, language }),
  });

  if (!response.ok) throw await parseError(response);
  return response.json();
}

// --> Get job status
export async function getJobStatus(jobId) {
  const response = await fetch(`${API_BASE_URL}/jobs/${jobId}`, {
    headers: authHeaders(),
  });

  if (!response.ok) throw await parseError(response);
  return response.json();
}

// --> Submit a repository (GitHub URL or .zip upload) for analysis
export async function submitRepoAnalysis(githubUrl, file) {
  const form = new FormData();
  if (githubUrl) form.append('github_url', githubUrl);
  else if (file) form.append('file', file);
  else throw new Error('Provide a GitHub URL or a .zip file.');

  const response = await fetch(`${API_BASE_URL}/analyze-repo`, {
    method: 'POST',
    headers: authHeaders(),
    body: form, // browser sets multipart boundary automatically
  });

  if (!response.ok) throw await parseError(response);
  return response.json();
}

// --> Fetch the signed-in user's profile
export async function fetchMe() {
  const response = await fetch(`${API_BASE_URL}/auth/me`, { headers: authHeaders() });
  if (!response.ok) {
    if (response.status === 401) clearToken();
    return null;
  }
  return response.json();
}
