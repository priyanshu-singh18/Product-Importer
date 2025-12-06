import { useState, useEffect, useRef } from "react";
import {
  generatePresignUrl,
  uploadToStorage,
  completeUpload,
  getImports,
  deleteImport,
  getImportErrors,
  getImportProducts,
} from "../services/api";
import "./ImportsPage.css";

function ImportsPage() {
  const [file, setFile] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [progress, setProgress] = useState(0);
  const [imports, setImports] = useState([]);
  const [selectedJob, setSelectedJob] = useState(null);
  const [jobStatus, setJobStatus] = useState({});
  const [showModal, setShowModal] = useState(false);
  const [modalData, setModalData] = useState({ type: null, data: null });

  // Use ref to store WebSocket connections (doesn't cause re-renders)
  const activeWebSockets = useRef({});

  useEffect(() => {
    loadImports();
  }, []);

  useEffect(() => {
    // Connect to WebSocket for any running or pending jobs
    const runningJobs = imports.filter(
      (job) => job.status === "running" || job.status === "pending"
    );

    runningJobs.forEach((job) => {
      if (!activeWebSockets.current[job.id]) {
        connectWebSocket(job.id);
      }
    });

    // Cleanup: ONLY close sockets for jobs that are no longer running
    const currentRunningIds = new Set(runningJobs.map((j) => j.id));
    Object.keys(activeWebSockets.current).forEach((jobId) => {
      if (!currentRunningIds.has(jobId)) {
        const socket = activeWebSockets.current[jobId];
        if (socket && socket.readyState === WebSocket.OPEN) {
          console.log(`Closing WebSocket for completed job ${jobId}`);
          socket.close();
        }
        delete activeWebSockets.current[jobId];
      }
    });
  }, [imports]);

  // Cleanup all sockets on component unmount
  useEffect(() => {
    return () => {
      console.log("Component unmounting, closing all WebSockets");
      Object.values(activeWebSockets.current).forEach((socket) => {
        if (socket && socket.readyState === WebSocket.OPEN) {
          socket.close();
        }
      });
      activeWebSockets.current = {};
    };
  }, []);

  const loadImports = async () => {
    try {
      const response = await getImports();
      setImports(response.data.results);
    } catch (error) {
      console.error("Failed to load imports:", error);
    }
  };

  const connectWebSocket = (jobId) => {
    // Don't create duplicate connections
    if (activeWebSockets.current[jobId]) {
      console.log(`WebSocket already connected for job ${jobId}`);
      return;
    }

    const wsUrl = `ws://localhost:8000/ws/import/${jobId}/`;
    console.log(`Connecting WebSocket for job ${jobId}...`);
    const socket = new WebSocket(wsUrl);

    socket.onopen = () => {
      console.log(`✓ WebSocket connected for job ${jobId}`);
      activeWebSockets.current[jobId] = socket;
    };

    socket.onmessage = (event) => {
      const data = JSON.parse(event.data);
      console.log(`WebSocket update for job ${jobId}:`, data);

      if (data.type !== "connection") {
        // Update job status with latest data
        setJobStatus((prev) => ({ ...prev, [jobId]: data }));

        // Update imports array to reflect new status
        setImports((prevImports) =>
          prevImports.map((job) =>
            job.id === jobId ? { ...job, ...data } : job
          )
        );

        // If completed or failed, reload imports list
        if (data.status === "completed" || data.status === "failed") {
          console.log(`✓ Job ${jobId} finished with status: ${data.status}`);
          // Reload to get final stats
          setTimeout(() => {
            loadImports();
          }, 1000);
          // Socket will be closed by cleanup logic when imports updates
        }
      }
    };

    socket.onerror = (error) => {
      console.error(`WebSocket error for job ${jobId}:`, error);
    };

    socket.onclose = () => {
      console.log(`WebSocket closed for job ${jobId}`);
      delete activeWebSockets.current[jobId];
    };
  };

  const handleFileSelect = (e) => {
    const selectedFile = e.target.files[0];
    if (selectedFile && selectedFile.name.endsWith(".csv")) {
      setFile(selectedFile);
    } else {
      alert("Please select a CSV file");
    }
  };

  const handleUpload = async () => {
    if (!file) return;

    setUploading(true);
    try {
      // Step 1: Get presigned URL
      const presignResponse = await generatePresignUrl(file.name);
      const { job_id, upload_url, fields } = presignResponse.data;

      // Step 2: Upload to storage
      await uploadToStorage(
        { upload_url, fields, job_id },
        file,
        (progressEvent) => {
          const percent = Math.round(
            (progressEvent.loaded * 100) / progressEvent.total
          );
          setProgress(percent);
        }
      );

      // Step 3: Complete upload
      const completeResponse = await completeUpload(job_id);
      setSelectedJob(completeResponse.data);

      // Reset form
      setFile(null);
      setProgress(0);

      // Reload imports and connect WebSocket
      await loadImports();
      setTimeout(() => connectWebSocket(job_id), 500);
    } catch (error) {
      console.error("Upload failed:", error);
      alert("Upload failed: " + error.message);
    } finally {
      setUploading(false);
    }
  };

  const handleDelete = async (id) => {
    if (!confirm("Delete this import job?")) return;
    try {
      await deleteImport(id);
      loadImports();
    } catch (error) {
      alert("Failed to delete: " + error.message);
    }
  };

  const showErrors = async (jobId) => {
    try {
      const response = await getImportErrors(jobId);
      setModalData({ type: "errors", data: response.data.errors });
      setShowModal(true);
    } catch (error) {
      alert("Failed to load errors");
    }
  };

  const showProducts = async (jobId, page = 1) => {
    try {
      const response = await getImportProducts(jobId, { page, page_size: 10 });
      setModalData({ type: "products", data: response.data, jobId });
      setShowModal(true);
    } catch (error) {
      alert("Failed to load products");
    }
  };

  const formatDate = (dateString) => {
    const date = new Date(dateString);
    const now = new Date();
    const diff = now - date;
    const minutes = Math.floor(diff / 60000);
    const hours = Math.floor(diff / 3600000);

    if (minutes < 1) return "Just now";
    if (minutes < 60) return `${minutes}m ago`;
    if (hours < 24) return `${hours}h ago`;
    return date.toLocaleDateString();
  };

  return (
    <div className="imports-page">
      <div className="upload-section">
        <h2>Upload CSV File</h2>
        <div className="upload-area">
          <input
            type="file"
            accept=".csv"
            onChange={handleFileSelect}
            disabled={uploading}
          />
          {file && (
            <div className="file-info">
              <p>
                {file.name} ({(file.size / 1024).toFixed(2)} KB)
              </p>
              <button onClick={handleUpload} disabled={uploading}>
                {uploading ? "Uploading..." : "Start Upload"}
              </button>
            </div>
          )}
          {uploading && (
            <div className="upload-progress">
              <div className="upload-progress-bar">
                <div
                  className="upload-progress-fill"
                  style={{ width: `${progress}%` }}
                ></div>
              </div>
              <p className="upload-progress-text">
                Uploading to storage: {progress}%
              </p>
            </div>
          )}
        </div>
      </div>

      <div className="imports-list">
        <div className="section-header">
          <h2>Recent Imports ({imports.length})</h2>
          <button onClick={loadImports} className="btn-refresh">
            Refresh
          </button>
        </div>

        <div className="imports-grid">
          {imports.map((job) => {
            const status = jobStatus[job.id] || job;
            return (
              <div key={job.id} className={`import-card ${status.status}`}>
                <div className="import-header">
                  <strong>{job.filename}</strong>
                  <span className="import-time">
                    {formatDate(job.created_at)}
                  </span>
                </div>

                <div className="import-stats">
                  <div>
                    Status: <strong>{status.status}</strong>
                  </div>
                  <div>
                    Progress:{" "}
                    <strong>{Math.round(status.percent || 0)}%</strong>
                  </div>
                  <div>
                    Created: <strong>{status.created_count || 0}</strong>
                  </div>
                  <div>
                    Updated: <strong>{status.updated_count || 0}</strong>
                  </div>
                  {status.error_count > 0 && (
                    <div style={{ color: "#e74c3c" }}>
                      Errors: <strong>{status.error_count}</strong>
                    </div>
                  )}
                </div>

                {status.status === "running" && (
                  <div className="progress-bar">
                    <div
                      className="progress-fill"
                      style={{ width: `${status.percent || 0}%` }}
                    ></div>
                  </div>
                )}

                <div className="import-actions">
                  {status.error_count > 0 && (
                    <button
                      onClick={() => showErrors(job.id)}
                      className="btn-errors"
                    >
                      View Errors
                    </button>
                  )}
                  {status.status === "completed" && (
                    <button
                      onClick={() => showProducts(job.id)}
                      className="btn-products"
                    >
                      View Products
                    </button>
                  )}
                  {["failed", "pending", "pending_upload"].includes(
                    status.status
                  ) && (
                    <button
                      onClick={() => handleDelete(job.id)}
                      className="btn-delete"
                    >
                      Delete
                    </button>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Modal */}
      {showModal && (
        <div className="modal-overlay" onClick={() => setShowModal(false)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h3>
                {modalData.type === "errors"
                  ? "Import Errors"
                  : "Imported Products"}
              </h3>
              <button
                onClick={() => setShowModal(false)}
                className="modal-close"
              >
                ×
              </button>
            </div>

            <div className="modal-body">
              {modalData.type === "errors" && (
                <table className="data-table">
                  <thead>
                    <tr>
                      <th>Row</th>
                      <th>SKU</th>
                      <th>Error</th>
                    </tr>
                  </thead>
                  <tbody>
                    {modalData.data.map((err, idx) => (
                      <tr key={idx}>
                        <td>{err.row_number}</td>
                        <td>{err.sku || "-"}</td>
                        <td>{err.error_message}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}

              {modalData.type === "products" && (
                <>
                  <table className="data-table">
                    <thead>
                      <tr>
                        <th>SKU</th>
                        <th>Name</th>
                        <th>Price</th>
                        <th>Status</th>
                      </tr>
                    </thead>
                    <tbody>
                      {modalData.data.results.map((product) => (
                        <tr key={product.id}>
                          <td>
                            <strong>{product.sku}</strong>
                          </td>
                          <td>{product.name || "-"}</td>
                          <td>{product.price ? `$${product.price}` : "-"}</td>
                          <td>
                            <span
                              className={`badge ${
                                product.active ? "active" : "inactive"
                              }`}
                            >
                              {product.active ? "Active" : "Inactive"}
                            </span>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>

                  <div className="pagination">
                    <button
                      disabled={!modalData.data.previous}
                      onClick={() =>
                        showProducts(modalData.jobId, modalData.data.page - 1)
                      }
                    >
                      Previous
                    </button>
                    <span>
                      Page {modalData.data.page} of {modalData.data.total_pages}
                    </span>
                    <button
                      disabled={!modalData.data.next}
                      onClick={() =>
                        showProducts(modalData.jobId, modalData.data.page + 1)
                      }
                    >
                      Next
                    </button>
                  </div>
                </>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default ImportsPage;
