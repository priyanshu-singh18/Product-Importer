import { BrowserRouter, Routes, Route, Link } from "react-router-dom";
import ImportsPage from "./pages/ImportsPage";
import ProductsPage from "./pages/ProductsPage";
import WebhooksPage from "./pages/WebhooksPage";
import "./App.css";

function App() {
  return (
    <BrowserRouter>
      <div className="app">
        <nav className="navbar">
          <div className="nav-brand">
            <h1>Product Importer</h1>
          </div>
          <div className="nav-links">
            <Link to="/">Imports</Link>
            <Link to="/products">Products</Link>
            <Link to="/webhooks">Webhooks</Link>
          </div>
        </nav>

        <Routes>
          <Route path="/" element={<ImportsPage />} />
          <Route path="/products" element={<ProductsPage />} />
          <Route path="/webhooks" element={<WebhooksPage />} />
        </Routes>
      </div>
    </BrowserRouter>
  );
}

export default App;
