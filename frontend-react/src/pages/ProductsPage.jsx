import { useState, useEffect } from "react";
import {
  getProducts,
  deleteProduct,
  bulkDeleteProducts,
  getImports,
} from "../services/api";
import "./ProductsPage.css";

function ProductsPage() {
  const [products, setProducts] = useState([]);
  const [totalCount, setTotalCount] = useState(0);
  const [currentPage, setCurrentPage] = useState(1);
  const [filters, setFilters] = useState({
    sku: "",
    name: "",
    import_job_id: "",
    active: "",
  });
  const [searchTerm, setSearchTerm] = useState("");
  const [importJobs, setImportJobs] = useState([]);
  const pageSize = 20;

  useEffect(() => {
    loadProducts();
    loadImportJobs();
  }, [currentPage, filters]);

  const loadProducts = async () => {
    try {
      const params = {
        page: currentPage,
        page_size: pageSize,
        ...Object.fromEntries(
          Object.entries(filters).filter(([_, v]) => v !== "")
        ),
      };

      const response = await getProducts(params);
      setProducts(response.data.results);
      setTotalCount(response.data.count);
    } catch (error) {
      console.error("Failed to load products:", error);
    }
  };

  const loadImportJobs = async () => {
    try {
      const response = await getImports();
      setImportJobs(
        response.data.results.filter((j) => j.status === "completed")
      );
    } catch (error) {
      console.error("Failed to load jobs:", error);
    }
  };

  const handleDelete = async (id, sku) => {
    if (!confirm(`Delete product "${sku}"?`)) return;
    try {
      await deleteProduct(id);
      loadProducts();
    } catch (error) {
      alert("Failed to delete: " + error.message);
    }
  };

  const handleBulkDelete = async () => {
    if (!confirm("⚠️ WARNING: Delete ALL products permanently?")) return;
    if (prompt('Type "DELETE" to confirm:') !== "DELETE") return;

    try {
      const response = await bulkDeleteProducts();
      alert(`Deleted ${response.data.deleted} products`);
      loadProducts();
    } catch (error) {
      alert("Failed to bulk delete: " + error.message);
    }
  };

  const handleFilterChange = (key, value) => {
    setFilters((prev) => ({ ...prev, [key]: value }));
    setCurrentPage(1);
  };

  const clearFilters = () => {
    setFilters({ sku: "", name: "", import_job_id: "", active: "" });
    setSearchTerm("");
    setCurrentPage(1);
  };

  const handleSearch = () => {
    // Send search term to both sku and name - backend uses OR logic
    setFilters((prev) => ({ ...prev, sku: searchTerm, name: searchTerm }));
    setCurrentPage(1);
  };

  const handleKeyPress = (e) => {
    if (e.key === "Enter") {
      handleSearch();
    }
  };

  const totalPages = Math.ceil(totalCount / pageSize);

  const formatDate = (dateString) => {
    return new Date(dateString).toLocaleDateString();
  };

  const truncate = (str, length) => {
    if (!str) return "-";
    return str.length > length ? str.substring(0, length) + "..." : str;
  };

  return (
    <div className="products-page">
      <div className="page-header">
        <h2>Products ({totalCount})</h2>
        <button onClick={handleBulkDelete} className="btn-danger">
          Delete All Products
        </button>
      </div>

      <div className="search-section">
        <div className="search-bar">
          <input
            type="text"
            placeholder="Search products by SKU or name..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            onKeyPress={handleKeyPress}
            className="search-input"
          />
          <button onClick={handleSearch} className="btn-search">
            Search
          </button>
          {searchTerm && (
            <button onClick={clearFilters} className="btn-clear">
              Clear
            </button>
          )}
        </div>
      </div>

      <div className="filters-section">
        <div className="filters-row">
          <select
            value={filters.import_job_id}
            onChange={(e) =>
              handleFilterChange("import_job_id", e.target.value)
            }
          >
            <option value="">All Import Jobs</option>
            {importJobs.map((job) => (
              <option key={job.id} value={job.id}>
                {truncate(job.filename, 30)} ({formatDate(job.created_at)})
              </option>
            ))}
          </select>

          <select
            value={filters.active}
            onChange={(e) => handleFilterChange("active", e.target.value)}
          >
            <option value="">All Status</option>
            <option value="true">Active</option>
            <option value="false">Inactive</option>
          </select>

          <button onClick={clearFilters} className="btn-secondary">
            Clear All Filters
          </button>
          <button onClick={loadProducts} className="btn-refresh">
            Refresh
          </button>
        </div>
      </div>

      <div className="products-table-container">
        <table className="products-table">
          <thead>
            <tr>
              <th>SKU</th>
              <th>Name</th>
              <th>Description</th>
              <th>Price</th>
              <th>Status</th>
              <th>Import Job</th>
              <th>Updated</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {products.length === 0 ? (
              <tr>
                <td
                  colSpan="8"
                  style={{ textAlign: "center", padding: "2rem" }}
                >
                  No products found
                </td>
              </tr>
            ) : (
              products.map((product) => (
                <tr key={product.id}>
                  <td>
                    <strong>{product.sku}</strong>
                  </td>
                  <td>{truncate(product.name, 30)}</td>
                  <td>{truncate(product.description, 40)}</td>
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
                  <td>
                    {product.last_import_job ? (
                      <span
                        className="job-link"
                        title={product.last_import_job.filename}
                      >
                        {truncate(product.last_import_job.filename, 20)}
                      </span>
                    ) : (
                      "-"
                    )}
                  </td>
                  <td>{formatDate(product.updated_at)}</td>
                  <td>
                    <button
                      onClick={() => handleDelete(product.id, product.sku)}
                      className="btn-delete-small"
                    >
                      Delete
                    </button>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {totalPages > 1 && (
        <div className="pagination">
          <button
            disabled={currentPage === 1}
            onClick={() => setCurrentPage((prev) => prev - 1)}
          >
            Previous
          </button>
          <span>
            Page {currentPage} of {totalPages} ({totalCount} total)
          </span>
          <button
            disabled={currentPage === totalPages}
            onClick={() => setCurrentPage((prev) => prev + 1)}
          >
            Next
          </button>
        </div>
      )}
    </div>
  );
}

export default ProductsPage;
