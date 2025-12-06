import axios from "axios";

const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

const api = axios.create({
  baseURL: `${API_URL}/api`,
  headers: {
    "Content-Type": "application/json",
  },
});

// Products
export const getProducts = (params) => api.get("/products/", { params });
export const getProduct = (id) => api.get(`/products/${id}/`);
export const deleteProduct = (id) => api.delete(`/products/${id}/`);
export const bulkDeleteProducts = () =>
  api.post(
    "/products/bulk-delete/",
    {},
    {
      headers: { "X-Confirm-Delete": "DELETE" },
    }
  );

// Imports
export const getImports = () => api.get("/imports/");
export const getImport = (id) => api.get(`/imports/${id}/`);
export const getImportErrors = (id) => api.get(`/imports/${id}/errors/`);
export const getImportProducts = (id, params) =>
  api.get(`/imports/${id}/products/`, { params });
export const deleteImport = (id) => api.delete(`/imports/${id}/delete/`);
export const generatePresignUrl = (filename) =>
  api.post("/imports/presign/", { filename });
export const completeUpload = (jobId) =>
  api.post(`/imports/${jobId}/complete/`);

// Webhooks
export const getWebhooks = () => api.get("/webhooks/");
export const createWebhook = (data) => api.post("/webhooks/", data);
export const deleteWebhook = (id) => api.delete(`/webhooks/${id}/`);
export const testWebhook = (id) => api.post(`/webhooks/${id}/test/`);

// Storage
export const uploadToStorage = async (presignData, file, onProgress) => {
  const formData = new FormData();

  if (presignData.fields && Object.keys(presignData.fields).length > 0) {
    // S3 upload
    Object.entries(presignData.fields).forEach(([key, value]) => {
      formData.append(key, value);
    });
    formData.append("file", file);

    return axios.post(presignData.upload_url, formData, {
      headers: { "Content-Type": "multipart/form-data" },
      onUploadProgress: onProgress,
    });
  } else {
    // Local storage
    formData.append("key", `imports/${presignData.job_id}/${file.name}`);
    formData.append("file", file);

    return axios.post(`${API_URL}/api/storage/upload/`, formData, {
      headers: { "Content-Type": "multipart/form-data" },
      onUploadProgress: onProgress,
    });
  }
};

export default api;
