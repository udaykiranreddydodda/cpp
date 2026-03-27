import { useState, useEffect } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import {
  ArrowLeft, ArrowDownCircle, ArrowUpCircle, Package, Edit3,
  Trash2, ChevronDown, ChevronUp,
} from 'lucide-react';
import * as api from '../api';
import toast from 'react-hot-toast';

export default function ProductDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [product, setProduct] = useState(null);
  const [movements, setMovements] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showEdit, setShowEdit] = useState(false);
  const [editForm, setEditForm] = useState({});
  const [editLoading, setEditLoading] = useState(false);
  const [deleteConfirm, setDeleteConfirm] = useState(false);

  // Stock movement form
  const [movType, setMovType] = useState('Intake');
  const [movQty, setMovQty] = useState('');
  const [movRef, setMovRef] = useState('');
  const [movNotes, setMovNotes] = useState('');
  const [movLoading, setMovLoading] = useState(false);

  useEffect(() => {
    fetchData();
  }, [id]);

  const fetchData = async () => {
    setLoading(true);
    try {
      const [prodRes, stockRes] = await Promise.all([
        api.getProduct(id),
        api.getStockHistory(id),
      ]);
      const prod = prodRes.data.product || prodRes.data;
      setProduct(prod);
      setEditForm({
        name: prod.name || '',
        sku: prod.sku || '',
        category: prod.category || 'Other',
        price: prod.price || 0,
        description: prod.description || '',
        minStock: prod.minStock || 0,
        maxStock: prod.maxStock || 100,
        supplier: prod.supplier || '',
      });
      setMovements(stockRes.data.movements || stockRes.data || []);
    } catch {
      toast.error('Failed to load product');
      navigate('/products');
    } finally {
      setLoading(false);
    }
  };

  const handleMovement = async (e) => {
    e.preventDefault();
    const qty = parseInt(movQty);
    if (!qty || qty <= 0) {
      toast.error('Enter a valid quantity');
      return;
    }
    setMovLoading(true);
    try {
      await api.addStockMovement(id, {
        type: movType,
        quantity: qty,
        reference: movRef,
        notes: movNotes,
      });
      toast.success(`Stock ${movType.toLowerCase()} recorded`);
      setMovQty('');
      setMovRef('');
      setMovNotes('');
      fetchData();
    } catch (err) {
      toast.error(err.response?.data?.message || 'Failed to add movement');
    } finally {
      setMovLoading(false);
    }
  };

  const handleEdit = async (e) => {
    e.preventDefault();
    setEditLoading(true);
    try {
      await api.updateProduct(id, {
        ...editForm,
        price: parseFloat(editForm.price) || 0,
        minStock: parseInt(editForm.minStock) || 0,
        maxStock: parseInt(editForm.maxStock) || 100,
      });
      toast.success('Product updated');
      setShowEdit(false);
      fetchData();
    } catch (err) {
      toast.error(err.response?.data?.message || 'Update failed');
    } finally {
      setEditLoading(false);
    }
  };

  const handleDelete = async () => {
    try {
      await api.deleteProduct(id);
      toast.success('Product deleted');
      navigate('/products');
    } catch {
      toast.error('Failed to delete product');
    }
  };

  const getStockStatus = () => {
    if (!product) return 'normal';
    if (product.currentStock <= (product.minStock || 0)) return 'critical';
    if (product.currentStock <= (product.minStock || 0) * 1.5) return 'low';
    return 'normal';
  };

  const statusConfig = {
    critical: { label: 'Critical', bg: 'bg-red-100', text: 'text-red-700' },
    low: { label: 'Low Stock', bg: 'bg-amber-100', text: 'text-amber-700' },
    normal: { label: 'In Stock', bg: 'bg-green-100', text: 'text-green-700' },
  };

  if (loading) {
    return (
      <div className="space-y-6">
        <div className="skeleton h-6 w-32"></div>
        <div className="skeleton h-10 w-64"></div>
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <div className="skeleton h-64 rounded-lg"></div>
          <div className="skeleton h-64 rounded-lg"></div>
        </div>
      </div>
    );
  }

  if (!product) return null;

  const status = getStockStatus();
  const sc = statusConfig[status];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <Link to="/products" className="inline-flex items-center gap-1 text-sm text-gray-500 hover:text-gray-700 mb-3">
          <ArrowLeft className="w-4 h-4" />
          Back to Products
        </Link>
        <div className="flex items-center gap-3">
          <h1 className="text-2xl font-bold text-gray-900">{product.name}</h1>
          <span className="text-xs font-mono bg-gray-100 text-gray-500 px-2 py-1 rounded">{product.sku}</span>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Product info */}
        <div className="bg-white border border-gray-200 rounded-lg p-6">
          <h2 className="text-base font-semibold text-gray-900 mb-4">Product Details</h2>
          <dl className="space-y-3 text-sm">
            <div className="flex justify-between">
              <dt className="text-gray-500">Category</dt>
              <dd className="font-medium text-gray-900">{product.category}</dd>
            </div>
            <div className="flex justify-between">
              <dt className="text-gray-500">Price</dt>
              <dd className="font-medium text-gray-900">${(product.price || 0).toLocaleString()}</dd>
            </div>
            <div className="flex justify-between">
              <dt className="text-gray-500">Supplier</dt>
              <dd className="font-medium text-gray-900">{product.supplier || '-'}</dd>
            </div>
            <div className="flex justify-between">
              <dt className="text-gray-500">Min Stock</dt>
              <dd className="font-medium text-gray-900">{product.minStock ?? 0}</dd>
            </div>
            <div className="flex justify-between">
              <dt className="text-gray-500">Max Stock</dt>
              <dd className="font-medium text-gray-900">{product.maxStock ?? 100}</dd>
            </div>
          </dl>
          {product.description && (
            <p className="mt-4 pt-4 border-t border-gray-100 text-sm text-gray-600">{product.description}</p>
          )}
        </div>

        {/* Current stock */}
        <div className="bg-white border border-gray-200 rounded-lg p-6 flex flex-col items-center justify-center text-center">
          <p className="text-sm text-gray-500 mb-2">Current Stock</p>
          <p className="text-5xl font-bold text-gray-900 mb-3">{product.currentStock ?? 0}</p>
          <span className={`inline-flex px-3 py-1 text-sm font-medium rounded-full ${sc.bg} ${sc.text}`}>
            {sc.label}
          </span>
        </div>

        {/* Stock movement form */}
        <div className="bg-white border border-gray-200 rounded-lg p-6">
          <h2 className="text-base font-semibold text-gray-900 mb-4">Add Stock Movement</h2>
          <form onSubmit={handleMovement} className="space-y-3">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Type</label>
              <select
                value={movType}
                onChange={(e) => setMovType(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="Intake">Intake</option>
                <option value="Dispatch">Dispatch</option>
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Quantity</label>
              <input
                type="number"
                min="1"
                value={movQty}
                onChange={(e) => setMovQty(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="Enter quantity"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Reference</label>
              <input
                value={movRef}
                onChange={(e) => setMovRef(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="PO-12345"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Notes</label>
              <input
                value={movNotes}
                onChange={(e) => setMovNotes(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="Optional notes"
              />
            </div>
            <button
              type="submit"
              disabled={movLoading}
              className={`w-full py-2.5 text-white text-sm font-medium rounded-lg transition-colors disabled:opacity-50 ${
                movType === 'Intake'
                  ? 'bg-green-600 hover:bg-green-700'
                  : 'bg-red-500 hover:bg-red-600'
              }`}
            >
              {movLoading ? 'Processing...' : `Record ${movType}`}
            </button>
          </form>
        </div>
      </div>

      {/* Movement history */}
      <div>
        <h2 className="text-lg font-semibold text-gray-900 mb-3">Movement History</h2>
        <div className="bg-white border border-gray-200 rounded-lg overflow-hidden">
          {movements.length > 0 ? (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-gray-100 bg-gray-50">
                    <th className="text-left py-3 px-4 font-medium text-gray-600">Date</th>
                    <th className="text-left py-3 px-4 font-medium text-gray-600">Type</th>
                    <th className="text-left py-3 px-4 font-medium text-gray-600">Quantity</th>
                    <th className="text-left py-3 px-4 font-medium text-gray-600">Reference</th>
                    <th className="text-left py-3 px-4 font-medium text-gray-600">Performed By</th>
                  </tr>
                </thead>
                <tbody>
                  {movements.map((mov, i) => (
                    <tr key={i} className="border-b border-gray-50 hover:bg-gray-50">
                      <td className="py-3 px-4 text-gray-600">
                        {new Date(mov.date || mov.createdAt).toLocaleDateString()}
                      </td>
                      <td className="py-3 px-4">
                        <span className={`inline-flex items-center gap-1 text-xs font-medium px-2 py-0.5 rounded-full ${
                          mov.type === 'Intake' || mov.type === 'intake'
                            ? 'bg-green-100 text-green-700'
                            : 'bg-red-100 text-red-700'
                        }`}>
                          {mov.type === 'Intake' || mov.type === 'intake' ? (
                            <ArrowDownCircle className="w-3 h-3" />
                          ) : (
                            <ArrowUpCircle className="w-3 h-3" />
                          )}
                          {mov.type}
                        </span>
                      </td>
                      <td className="py-3 px-4 font-medium text-gray-900">{mov.quantity}</td>
                      <td className="py-3 px-4 text-gray-500">{mov.reference || '-'}</td>
                      <td className="py-3 px-4 text-gray-500">{mov.performedBy?.username || mov.performedBy || '-'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="py-12 text-center text-gray-400">
              <Package className="w-8 h-8 mx-auto mb-2 opacity-50" />
              <p>No stock movements yet</p>
            </div>
          )}
        </div>
      </div>

      {/* Edit section */}
      <div className="bg-white border border-gray-200 rounded-lg">
        <button
          onClick={() => setShowEdit(!showEdit)}
          className="w-full flex items-center justify-between p-5 text-left"
        >
          <div className="flex items-center gap-2">
            <Edit3 className="w-4 h-4 text-gray-500" />
            <span className="text-base font-semibold text-gray-900">Edit Product</span>
          </div>
          {showEdit ? <ChevronUp className="w-5 h-5 text-gray-400" /> : <ChevronDown className="w-5 h-5 text-gray-400" />}
        </button>
        {showEdit && (
          <form onSubmit={handleEdit} className="px-5 pb-5 space-y-4 border-t border-gray-100 pt-5">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Name</label>
                <input value={editForm.name} onChange={(e) => setEditForm({ ...editForm, name: e.target.value })} className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500" />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">SKU</label>
                <input value={editForm.sku} onChange={(e) => setEditForm({ ...editForm, sku: e.target.value })} className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500" />
              </div>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Category</label>
                <select value={editForm.category} onChange={(e) => setEditForm({ ...editForm, category: e.target.value })} className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-blue-500">
                  {['Electronics', 'Clothing', 'Food', 'Furniture', 'Tools', 'Office', 'Other'].map((c) => (
                    <option key={c} value={c}>{c}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Price</label>
                <input type="number" step="0.01" value={editForm.price} onChange={(e) => setEditForm({ ...editForm, price: e.target.value })} className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500" />
              </div>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Description</label>
              <textarea value={editForm.description} onChange={(e) => setEditForm({ ...editForm, description: e.target.value })} rows={2} className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500" />
            </div>
            <div className="grid grid-cols-3 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Min Stock</label>
                <input type="number" value={editForm.minStock} onChange={(e) => setEditForm({ ...editForm, minStock: e.target.value })} className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500" />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Max Stock</label>
                <input type="number" value={editForm.maxStock} onChange={(e) => setEditForm({ ...editForm, maxStock: e.target.value })} className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500" />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Supplier</label>
                <input value={editForm.supplier} onChange={(e) => setEditForm({ ...editForm, supplier: e.target.value })} className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500" />
              </div>
            </div>
            <div className="flex justify-end gap-3 pt-2">
              <button type="button" onClick={() => setShowEdit(false)} className="px-4 py-2 text-sm text-gray-600 font-medium">Cancel</button>
              <button type="submit" disabled={editLoading} className="px-5 py-2 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 disabled:opacity-50">
                {editLoading ? 'Saving...' : 'Save Changes'}
              </button>
            </div>
          </form>
        )}
      </div>

      {/* Delete */}
      <div className="bg-white border border-red-200 rounded-lg p-5">
        <h3 className="text-base font-semibold text-red-600 mb-2">Danger Zone</h3>
        <p className="text-sm text-gray-500 mb-4">Permanently delete this product and all its movement history.</p>
        {!deleteConfirm ? (
          <button
            onClick={() => setDeleteConfirm(true)}
            className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-red-600 border border-red-300 rounded-lg hover:bg-red-50 transition-colors"
          >
            <Trash2 className="w-4 h-4" />
            Delete Product
          </button>
        ) : (
          <div className="flex items-center gap-3">
            <span className="text-sm text-red-600 font-medium">Are you sure?</span>
            <button onClick={handleDelete} className="px-4 py-2 bg-red-500 text-white text-sm font-medium rounded-lg hover:bg-red-600">
              Yes, Delete
            </button>
            <button onClick={() => setDeleteConfirm(false)} className="px-4 py-2 text-sm text-gray-600 font-medium">
              Cancel
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
