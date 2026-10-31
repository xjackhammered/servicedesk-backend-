import { api } from './client';

export const login = (username, password) =>
  api('/auth/login/', { method: 'POST', body: { username, password }, auth: false });
export const register = (body) => api('/auth/register/', { method: 'POST', body, auth: false });
export const fetchMe = () => api('/auth/me/');

export const listRequests = (params) => api('/requests/', { params });
export const getRequest = (id) => api(`/requests/${id}/`);
export const getHistory = (id) => api(`/requests/${id}/history/`);
export const getStats = () => api('/requests/stats/');
export const createRequest = (body) => api('/requests/', { method: 'POST', body });
export const cancelRequest = (id) => api(`/requests/${id}/cancel/`, { method: 'POST' });
export const retryRequest = (id) => api(`/requests/${id}/retry/`, { method: 'POST' });
