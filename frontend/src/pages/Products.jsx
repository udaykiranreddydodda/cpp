import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { Plus, Search, Package, X } from 'lucide-react';
import * as api from '../api';
import toast from 'react-hot-toast';

const CATEGORIES = ['All', 'Electronics', 'Clothing', 'Food', 'Furniture', 'Tools', 'Office', 'Other'];

export default function Products() {
  const [products, setProducts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [category, setCategory] = useState('All');
  const [showModal, setShowModal] = useState(false);
  const [formLoading, setFormLoading] = useState(false);
  const [form, setForm] = useState({
    name: '', sku: '', category: 'Electronics', price: '', description: '',
    minStock: '', maxStock: '', currentStock: '', supplier: '',
  });

  useEffect(() => {
    fetchProducts();
  }, []);

  const fetchProducts = async () => {
    try {
      const res = await api.getProducts();
      setProducts(res.data.products || res.data || []);
    } catch {
      toast.error('Failed to load products');
    } finally {
      setLoading(false);
    }
  };

  const handleCreate = async (e) => {
    e.preventDefault();
    if (!form.name || !form.sku) {
      toast.error('Name and SKU are required');
      return;
    }
    setFormLoading(true);
    try {
      const payload = {
        ...form,
        price: parseFloat(form.price) || 0,
        minStock: parseInt(form.minStock) || 0,
        maxStock: parseInt(form.maxStock) || 100,
        currentStock: parseInt(form.currentStock) || 0,
      };
      await api.createProduct(payload);
      toast.success('Product created');
      setShowModal(false);
      setForm({ name: '', sku: '', category: 'Electronics', price: '', description: '', minStock: '', maxStock: '', currentStock: '', supplier: '' });
      fetchProducts();
    } catch (err) {
      toast.error(err.response?.data?.message || 'Failed to create product');
    } finally {
      setFormLoading(false);
    }
  };

  const updateForm = (field) => (e) => setForm({ ...form, [field]: e.target.value });

  const filtered = products.filter((p) => {
    const matchSearch = p.name?.toLowerCase().includes(search.toLowerCase()) ||
      p.sku?.toLowerCase().includes(search.toLowerCase());
    const matchCat = category === 'All' || p.category === category;
    return matchSearch && matchCat;
  });

  const getStockStatus = (p) => {
    if (p.currentStock <= (p.minStock || 0)) return 'critical';
    if (p.currentStock <= (p.minStock || 0) * 1.5) return 'low';
    return 'normal';
  };

  const getStockBarColor = (status) => {
    if (status === 'critical') return 'bg-red-500';
    if (status === 'low') return 'bg-amber-500';
    return 'bg-green-500';
  };

  const getStockPercent = (p) => {
    const max = p.maxStock || 100;
    return Math.min(100, Math.round((p.currentStock / max) * 100));
  };

  if (loading) {
    return (
      <div className="space-y-6">
        <div className="skeleton h-8 w-40"></div>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {[1, 2, 3, 4, 5, 6].map((i) => (
            <div key={i} className="skeleton h-44 rounded-lg"></div>
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900">Products</h1>
        <button
          onClick={() => setShowModal(true)}
          className="flex items-center gap-2 px-4 py-2.5 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 transition-colors"
        >
          <Plus className="w-4 h-4" />
          Add Product
        </button>
      </div>

      {/* Search */}
      <div className="relative max-w-md">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
        <input
          type="text"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Search products..."
          className="w-full pl-10 pr-4 py-2.5 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 bg-white"
        />
      </div>

      {/* Category pills */}
      <div className="flex flex-wrap gap-2">
        {CATEGORIES.map((cat) => (
          <button
            key={cat}
            onClick={() => setCategory(cat)}
            className={`px-3 py-1.5 text-sm rounded-full font-medium transition-colors ${
              category === cat
                ? 'bg-blue-600 text-white'
                : 'bg-white border border-gray-200 text-gray-600 hover:bg-gray-50'
            }`}
          >
            {cat}
          </button>
        ))}
      </div>

      {/* Product grid */}
      {filtered.length === 0 ? (
        <div className="text-center py-16">
          <Package className="w-12 h-12 text-gray-300 mx-auto mb-3" />
          <p className="text-gray-500">No products found</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {filtered.map((product) => {
            const status = getStockStatus(product);
            return (
              <Link
                key={product._id}
                to={`/products/${product._id}`}
                className="bg-white border border-gray-200 rounded-lg p-5 hover:shadow-md transition-shadow block"
              >
                <div className="flex items-start justify-between mb-3">
                  <div className="min-w-0 flex-1">
                    <h3 className="font-semibold text-gray-900 truncate">{product.name}</h3>
                    <p className="text-xs text-gray-400 mt-0.5">{product.sku}</p>
                  </div>
                  <span className="text-xs font-medium px-2 py-0.5 bg-gray-100 text-gray-600 rounded-full ml-2 flex-shrink-0">
                    {product.category}
                  </span>
                </div>

                {/* Stock bar */}
                <div className="mb-3">
                  <div className="w-full bg-gray-200 h-2 rounded-full overflow-hidden">
                    <div
                      className={`h-full rounded-full ${getStockBarColor(status)}`}
                      style={{ width: `${getStockPercent(product)}%` }}
                    ></div>
                  </div>
                </div>

                <div className="flex items-center justify-between text-sm">
                  <span className="text-gray-900 font-medium">
                    ${(product.price || 0).toLocaleString()}
                  </span>
                  <span className="text-gray-500">
                    {product.currentStock} / {product.maxStock || 100}
                  </span>
                </div>
              </Link>
            );
          })}
        </div>
      )}

      {/* Add Product Modal */}
      {showModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 px-4">
          <div className="bg-white rounded-xl w-full max-w-lg max-h-[90vh] overflow-y-auto shadow-xl">
            <div className="flex items-center justify-between p-6 border-b border-gray-200">
              <h2 className="text-lg font-semibold text-gray-900">Add Product</h2>
              <button onClick={() => setShowModal(false)} className="text-gray-400 hover:text-gray-600">
                <X className="w-5 h-5" />
              </button>
            </div>
            <form onSubmit={handleCreate} className="p-6 space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Name *</label>
                  <input value={form.name} onChange={updateForm('name')} className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500" />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">SKU *</label>
                  <input value={form.sku} onChange={updateForm('sku')} className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500" />
                </div>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Category</label>
                  <select value={form.category} onChange={updateForm('category')} className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white">
                    {CATEGORIES.filter((c) => c !== 'All').map((c) => (
                      <option key={c} value={c}>{c}</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Price</label>
                  <input type="number" step="0.01" value={form.price} onChange={updateForm('price')} className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500" />
                </div>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Description</label>
                <textarea value={form.description} onChange={updateForm('description')} rows={2} className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500" />
              </div>
              <div className="grid grid-cols-3 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Min Stock</label>
                  <input type="number" value={form.minStock} onChange={updateForm('minStock')} className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500" />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Max Stock</label>
                  <input type="number" value={form.maxStock} onChange={updateForm('maxStock')} className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500" />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Current Stock</label>
                  <input type="number" value={form.currentStock} onChange={updateForm('currentStock')} className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500" />
                </div>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Supplier Name</label>
                <input value={form.supplier} onChange={updateForm('supplier')} className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500" />
              </div>
              <div className="flex justify-end gap-3 pt-2">
                <button type="button" onClick={() => setShowModal(false)} className="px-4 py-2 text-sm text-gray-600 hover:text-gray-800 font-medium">
                  Cancel
                </button>
                <button type="submit" disabled={formLoading} className="px-5 py-2 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 disabled:opacity-50">
                  {formLoading ? 'Creating...' : 'Create Product'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
