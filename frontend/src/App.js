import React, { useState, useMemo, useEffect } from 'react';
import './App.css';
import { Routes, Route, useNavigate, useParams } from 'react-router-dom';

// Mock data for testing when API is not available
const mockData = [
  {
    image_url: "https://f.nooncdn.com/p/pzsku/ZFD49F52791DB3A6FD1FFZ/45/_/1737627676/c67e4be2-5115-4d8c-9acd-55bcba9ab023.jpg?width=400&format=avif",
    name: "400g",
    origin: "Mutti Pasta Sauce Rossoro Tomatoes With Genovese Basil PDO",
    original_price: "22.50",
    price: "18.60",
    size: "400g",
    product_id: "mock1",
    description: "A delicious Italian pasta sauce made from Rossoro tomatoes and Genovese basil."
  },
  {
    image_url: "https://f.nooncdn.com/p/pzsku/ZFD49F52791DB3A6FD1FFZ/45/_/1737627676/c67e4be2-5115-4d8c-9acd-55bcba9ab023.jpg?width=400&format=avif",
    name: "500g",
    origin: "Organic Fresh Tomatoes Premium Quality",
    original_price: "",
    price: "12.99",
    size: "500g",
    product_id: "mock2",
    description: "Premium quality organic fresh tomatoes, perfect for salads and cooking."
  },
  {
    image_url: "https://f.nooncdn.com/p/pzsku/ZFD49F52791DB3A6FD1FFZ/45/_/1737627676/c67e4be2-5115-4d8c-9acd-55bcba9ab023.jpg?width=400&format=avif",
    name: "1kg",
    origin: "Cherry Tomatoes Sweet and Juicy",
    original_price: "15.99",
    price: "13.50",
    size: "1kg",
    product_id: "mock3",
    description: "Sweet and juicy cherry tomatoes, great for snacking."
  }
];

// Keyword extraction utility
function extractProductKeywords(productName, description, topN = 10) {
  const priorityWords = new Set([
    "fresh", "freshness", "convenience", "organic", "healthy", "fiber", 
    "vitamin", "low", "fat", "cholesterol", "potassium", "natural", "premium"
  ]);
  const nameWords = productName
    .toLowerCase()
    .replace(/[^a-z\s]/g, "")
    .split(/\s+/)
    .filter(w => w.length > 2);
  const stopwords = new Set([
    "a", "an", "the", "and", "or", "but", "of", "for", "to", "in", "on",
    "at", "with", "this", "that", "it", "its", "as", "by", "from",
    "was", "are", "be", "been", "their", "they", "you", "your", "day",
    "offers", "making", "perfect", "choice", "way", "stay", "ready", "light", "ideal"
  ]);
  
  // If description is empty or very short, fall back to using product name
  let textToProcess = description;
  if (!description || description.trim().length < 10) {
    textToProcess = productName;
  }
  
  const words = textToProcess
    .toLowerCase()
    .replace(/[^a-z\s]/g, "")
    .split(/\s+/)
    .filter(w => w.length > 2 && !stopwords.has(w));
  
  const freqMap = {};
  words.forEach((word, idx) => {
    let weight = 1;
    if (nameWords.includes(word)) weight += 3;
    if (priorityWords.has(word)) weight += 2;
    if (idx < 15) weight += 1;
    freqMap[word] = (freqMap[word] || 0) + weight;
  });
  
  const sorted = Object.entries(freqMap).sort((a, b) => b[1] - a[1]);
  const topWords = sorted.slice(0, topN).map(([word]) => word);
  const phrases = [];
  if (topWords.includes("potatoes") && topWords.includes("roasting")) {
    phrases.push("roasting potatoes");
  }
  if (topWords.includes("miss") && topWords.includes("blush")) {
    phrases.push("Miss Blush Potatoes");
  }
  return [...new Set([...topWords, ...phrases])];
}

function ProductList({ allFoodItems, loading, error, usingMockData, dataFullyLoaded, searchTerm, setSearchTerm, filteredItems, fetchAllFoodItems }) {
  const navigate = useNavigate();

  useEffect(() => {
    filteredItems.forEach((item, idx) => {
      console.log(`Product ${idx}: product_id=`, item.product_id);
    });
  }, [filteredItems]);

  return (
    <div className="container">
      <header className="header">
        <h1>🍽️ Food Search</h1>
        <p>Search through all available food items!</p>
        {usingMockData && (
          <p style={{ fontSize: '0.9rem', opacity: 0.8, marginTop: '10px' }}>
            ⚠️ Demo mode: Using sample data. Start your API server to see real data.
          </p>
        )}
      </header>
      <div className="search-section">
        <div className="search-container">
          <input
            type="text"
            placeholder="Search for food items..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="search-input"
            disabled={!dataFullyLoaded}
          />
          <span className="search-icon">🔍</span>
        </div>
      </div>
      <div className="results-info">
        {error && !usingMockData ? (
          <p className="error-message">❌ {error}</p>
        ) : dataFullyLoaded ? (
          <p>Showing {filteredItems.length} of {allFoodItems.length} items</p>
        ) : (
          ""
        )}
      </div>
      <div className="food-grid">
        {(loading || !dataFullyLoaded) ? (
          <div className="main-loader">
            <div className="main-loader-spinner"></div>
            <p>Loading all food items...</p>
          </div>
        ) : error && !usingMockData ? (
          <div className="no-results">
            <p>😕 {error}</p>
            <p>Please check if your API server is running on localhost:5000</p>
            <p>Check the browser console (F12) for more details</p>
            <button onClick={fetchAllFoodItems} className="retry-btn">Retry</button>
          </div>
        ) : filteredItems.length > 0 ? (
          filteredItems.map((item, index) => (
            item.product_id ? (
              <div key={item.product_id} className="food-card" style={{ cursor: 'pointer' }} onClick={() => navigate(`/product/${item.product_id}`, { state: { product: item } })}>
                <div className="food-image">
                  <img 
                    src={item.image_url} 
                    alt={item.name || item.origin || 'Food Item'}
                    onError={(e) => {
                      e.target.style.display = 'none';
                      e.target.nextSibling.style.display = 'block';
                    }}
                  />
                  <div className="food-emoji-fallback" style={{ display: 'none' }}>🍽️</div>
                </div>
                <h3 className="food-name">{item.name || item.origin}</h3>
                <p className="food-size">{item.size}</p>
                <div className="price-section">
                  {item.original_price && (
                    <span className="original-price">${item.original_price}</span>
                  )}
                  <span className="current-price">${item.price}</span>
                </div>
                <button className="order-btn">Add to Cart</button>
              </div>
            ) : (
              <div key={index} className="food-card" style={{ opacity: 0.5 }}>
                <div className="food-emoji-fallback">⚠️</div>
                <h3 className="food-name">Missing product_id</h3>
                <p style={{ color: 'red', fontSize: '0.9rem' }}>This product cannot be viewed in detail.</p>
              </div>
            )
          ))
        ) : searchTerm ? (
          <div className="no-results">
            <p>😕 No food items found matching "{searchTerm}".</p>
            <p>Try adjusting your search terms.</p>
          </div>
        ) : (
          <div className="no-results">
            <p>📦 No food items available.</p>
            <p>Please check your API connection.</p>
          </div>
        )}
      </div>
    </div>
  );
}

function ProductDetail() {
  const [product, setProduct] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const { product_id } = useParams();

  useEffect(() => {
    async function fetchProductDetail() {
      setLoading(true);
      setError(null);
      try {
        // Always fetch from backend for full data
        const response = await fetch(`/product-details/${product_id}`);
        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }
        const data = await response.json();
        setProduct(data);
      } catch (err) {
        setError('Failed to fetch product details.');
      } finally {
        setLoading(false);
      }
    }
    fetchProductDetail();
  }, [product_id]);

  if (loading) {
    return <div className="detail-loader"><div className="detail-loader-spinner"></div><p>Loading product details...</p></div>;
  }
  if (error) {
    return <div className="no-results"><p>😕 {error}</p></div>;
  }
  if (!product) {
    return <div className="no-results"><p>Product not found.</p></div>;
  }

  // Layout fields
  const name = product.name || product.title || product.origin || '';
  const size = product.size || product.weight || product.unit || '';
  const price = product.original_price && product.original_price !== '' ? product.original_price : product.price || '';
  const description = product.description || product.details || product.desc || '';
  const features = product.features || product.specs || product.attributes || [];

  // Merge description and features for keyword extraction
  const mergedText = [description, ...(Array.isArray(features) ? features : [])].join(' ');
  const topKeywords = extractProductKeywords(name, mergedText, 10);

  return (
    <div className="product-detail-bg">
      <div className="product-detail-card">
        <button className="back-btn" onClick={() => window.history.back()}>
          <span style={{fontSize: '1.2em', marginRight: '4px'}}>←</span>
        </button>
        <div className="product-detail-image">
          <img src={product.image_url} alt={name || 'Product'} />
        </div>
        <div className="product-detail-info">
          <div className="product-detail-title">{name}</div>
          {size && <div className="product-detail-size">{size}</div>}
          <div className="product-detail-row">
            {price && <div className="product-detail-price">₦ {price}</div>}
          </div>
          <div className="product-detail-description">{description}</div>
          {topKeywords.length > 0 && (
            <div className="product-keywords">
              {topKeywords.map((kw, i) => (
                <span className="keyword-chip" key={i}>{kw}</span>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function App() {
  const [searchTerm, setSearchTerm] = useState('');
  const [allFoodItems, setAllFoodItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [usingMockData, setUsingMockData] = useState(false);
  const [dataFullyLoaded, setDataFullyLoaded] = useState(false);

  const fetchAllFoodItems = async () => {
    setLoading(true);
    setError(null);
    setDataFullyLoaded(false);
    setAllFoodItems([]);
    try {
      const response = await fetch('/search');
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      const responseText = await response.text();
      if (responseText.trim().startsWith('<!DOCTYPE html>')) {
        setAllFoodItems(mockData);
        setUsingMockData(true);
        setDataFullyLoaded(true);
        return;
      }
      let data;
      try {
        data = JSON.parse(responseText);
      } catch {
        throw new Error('Invalid JSON response.');
      }
      let items = [];
      if (Array.isArray(data)) {
        items = data;
      } else if (data && typeof data === 'object') {
        const dataArray = Object.values(data).find(val => Array.isArray(val));
        if (dataArray) {
          items = dataArray;
        } else {
          items = [data];
        }
      }
      if (items && items.length > 0) {
        setAllFoodItems(items);
        setUsingMockData(false);
        setDataFullyLoaded(true);
      } else {
        throw new Error('No valid items found in API response');
      }
    } catch (err) {
      setAllFoodItems(mockData);
      setUsingMockData(true);
      setDataFullyLoaded(true);
      setError(`API server not available. Using demo data. Error: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAllFoodItems();
  }, []);

  const filteredItems = useMemo(() => {
    if (!searchTerm.trim()) {
      return allFoodItems;
    }
    const searchLower = searchTerm.toLowerCase();
    return allFoodItems.filter(item => {
      const name = (item.name || item.origin || '').toLowerCase();
      const size = (item.size || '').toLowerCase();
      return name.includes(searchLower) || size.includes(searchLower);
    });
  }, [searchTerm, allFoodItems]);

  return (
    <Routes>
      <Route path="/" element={
        <ProductList
          allFoodItems={allFoodItems}
          loading={loading}
          error={error}
          usingMockData={usingMockData}
          dataFullyLoaded={dataFullyLoaded}
          searchTerm={searchTerm}
          setSearchTerm={setSearchTerm}
          filteredItems={filteredItems}
          fetchAllFoodItems={fetchAllFoodItems}
        />
      } />
      <Route path="/product/:product_id" element={<ProductDetail />} />
    </Routes>
  );
}

export default App;
