import axios from 'axios';

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || '',
});

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('token');
      localStorage.removeItem('user');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

// Auth
export const register = (data) => api.post('/auth/register', data);
export const login = (data) => api.post('/auth/login', data);

// Products
export const getProducts = (params) => api.get('/products', { params });
export const createProduct = (data) => api.post('/products', data);
export const getProduct = (id) => api.get(`/products/${id}`);
export const updateProduct = (id, data) => api.put(`/products/${id}`, data);
export const deleteProduct = (id) => api.delete(`/products/${id}`);

// Stock
export const addStockMovement = (id, data) => api.post(`/products/${id}/stock`, data);
export const getStockHistory = (id) => api.get(`/products/${id}/stock`);

// Suppliers
export const getSuppliers = () => api.get('/suppliers');
export const createSupplier = (data) => api.post('/suppliers', data);
export const updateSupplier = (id, data) => api.put(`/suppliers/${id}`, data);
export const deleteSupplier = (id) => api.delete(`/suppliers/${id}`);

// Dashboard
export const getDashboard = () => api.get('/dashboard');

// Subscriptions
export const subscribe = (data) => api.post('/subscribe', data);
export const getSubscriberCount = () => api.get('/subscribe/count');

export default api;
