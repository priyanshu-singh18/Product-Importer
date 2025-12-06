import { useState, useEffect } from "react";
import {
  getWebhooks,
  createWebhook,
  deleteWebhook,
  testWebhook,
} from "../services/api";
import "./WebhooksPage.css";

function WebhooksPage() {
  const [webhooks, setWebhooks] = useState([]);
  const [showForm, setShowForm] = useState(false);
  const [formData, setFormData] = useState({
    name: "",
    url: "",
    event: "import.completed",
    secret: "",
    enabled: true,
  });
  const [testResults, setTestResults] = useState({});

  useEffect(() => {
    loadWebhooks();
  }, []);

  const loadWebhooks = async () => {
    try {
      const response = await getWebhooks();
      setWebhooks(response.data.results || []);
    } catch (error) {
      console.error("Failed to load webhooks:", error);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      await createWebhook(formData);
      setShowForm(false);
      setFormData({
        name: "",
        url: "",
        event: "import.completed",
        secret: "",
        enabled: true,
      });
      loadWebhooks();
      alert("Webhook created successfully!");
    } catch (error) {
      alert("Failed to create webhook: " + error.message);
    }
  };

  const handleDelete = async (id, name) => {
    if (!confirm(`Delete webhook "${name}"?`)) return;
    try {
      await deleteWebhook(id);
      loadWebhooks();
    } catch (error) {
      alert("Failed to delete: " + error.message);
    }
  };

  const handleTest = async (id, name) => {
    try {
      setTestResults((prev) => ({ ...prev, [id]: { testing: true } }));
      const response = await testWebhook(id);
      const data = response.data;
      setTestResults((prev) => ({
        ...prev,
        [id]: {
          testing: false,
          success: data.success,
          status_code: data.status_code,
          response_time_ms: data.response_time_ms,
        },
      }));
      setTimeout(() => {
        setTestResults((prev) => ({ ...prev, [id]: null }));
      }, 5000);
    } catch (error) {
      setTestResults((prev) => ({
        ...prev,
        [id]: { testing: false, success: false, error: error.message },
      }));
    }
  };

  return (
    <div className="webhooks-page">
      <div className="page-header">
        <h2>Webhooks ({webhooks.length})</h2>
        <button onClick={() => setShowForm(true)} className="btn-primary">
          + Add Webhook
        </button>
      </div>

      {showForm && (
        <div className="modal-overlay" onClick={() => setShowForm(false)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h3>Create Webhook</h3>
              <button
                onClick={() => setShowForm(false)}
                className="modal-close"
              >
                ×
              </button>
            </div>

            <form onSubmit={handleSubmit} className="webhook-form">
              <div className="form-group">
                <label>Name *</label>
                <input
                  type="text"
                  value={formData.name}
                  onChange={(e) =>
                    setFormData({ ...formData, name: e.target.value })
                  }
                  required
                  placeholder="My Webhook"
                />
              </div>

              <div className="form-group">
                <label>URL *</label>
                <input
                  type="url"
                  value={formData.url}
                  onChange={(e) =>
                    setFormData({ ...formData, url: e.target.value })
                  }
                  required
                  placeholder="https://example.com/webhook"
                />
              </div>

              <div className="form-group">
                <label>Event *</label>
                <select
                  value={formData.event}
                  onChange={(e) =>
                    setFormData({ ...formData, event: e.target.value })
                  }
                >
                  <option value="import.completed">Import Completed</option>
                  <option value="import.failed">Import Failed</option>
                  <option value="product.created">Product Created</option>
                  <option value="product.updated">Product Updated</option>
                </select>
              </div>

              <div className="form-group">
                <label>Secret (optional)</label>
                <input
                  type="text"
                  value={formData.secret}
                  onChange={(e) =>
                    setFormData({ ...formData, secret: e.target.value })
                  }
                  placeholder="For HMAC signing"
                />
              </div>

              <div className="form-group-checkbox">
                <label>
                  <input
                    type="checkbox"
                    checked={formData.enabled}
                    onChange={(e) =>
                      setFormData({ ...formData, enabled: e.target.checked })
                    }
                  />
                  Enabled
                </label>
              </div>

              <div className="form-actions">
                <button type="submit" className="btn-primary">
                  Create Webhook
                </button>
                <button
                  type="button"
                  onClick={() => setShowForm(false)}
                  className="btn-secondary"
                >
                  Cancel
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      <div className="webhooks-list">
        {webhooks.length === 0 ? (
          <div className="no-webhooks">
            <p>No webhooks configured</p>
            <p>Click "Add Webhook" to create your first webhook</p>
          </div>
        ) : (
          webhooks.map((webhook) => {
            const testResult = testResults[webhook.id];
            return (
              <div key={webhook.id} className="webhook-card">
                <div className="webhook-header">
                  <div>
                    <h3>{webhook.name}</h3>
                    <span
                      className={`webhook-status ${
                        webhook.enabled ? "enabled" : "disabled"
                      }`}
                    >
                      {webhook.enabled ? "Enabled" : "Disabled"}
                    </span>
                  </div>
                  <span className="webhook-event">{webhook.event}</span>
                </div>

                <div className="webhook-details">
                  <div className="webhook-detail">
                    <strong>URL:</strong>
                    <code>{webhook.url}</code>
                  </div>
                  <div className="webhook-detail">
                    <strong>Secret:</strong>
                    {webhook.secret ? (
                      <code>••••••••</code>
                    ) : (
                      <span className="text-muted">Not set</span>
                    )}
                  </div>
                </div>

                {testResult && !testResult.testing && (
                  <div
                    className={`test-result ${
                      testResult.success ? "success" : "error"
                    }`}
                  >
                    {testResult.success ? (
                      <>
                        ✓ Test successful - Status: {testResult.status_code} -
                        Response time: {testResult.response_time_ms}ms
                      </>
                    ) : (
                      <>✗ Test failed - {testResult.error}</>
                    )}
                  </div>
                )}

                <div className="webhook-actions">
                  <button
                    onClick={() => handleTest(webhook.id, webhook.name)}
                    className="btn-test"
                    disabled={testResult?.testing}
                  >
                    {testResult?.testing ? "Testing..." : "Test Webhook"}
                  </button>
                  <button
                    onClick={() => handleDelete(webhook.id, webhook.name)}
                    className="btn-delete"
                  >
                    Delete
                  </button>
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}

export default WebhooksPage;
