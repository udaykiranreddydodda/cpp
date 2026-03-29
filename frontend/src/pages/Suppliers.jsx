import { useState, useEffect } from 'react';
import { Plus, X, Truck, Edit3, Trash2, Mail, Phone, MapPin } from 'lucide-react';
import * as api from '../api';
import toast from 'react-hot-toast';

export default function Suppliers() {
  const [suppliers, setSuppliers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [editId, setEditId] = useState(null);
  const [formLoading, setFormLoading] = useState(false);
  const [deleteConfirm, setDeleteConfirm] = useState(null);
  const [form, setForm] = useState({ name: '', email: '', phone: '', address: '' });

  useEffect(() => {
    fetchSuppliers();
  }, []);

  const fetchSuppliers = async () => {
    try {
      const res = await api.getSuppliers();
      setSuppliers(res.data.suppliers || res.data || []);
    } catch {
      toast.error('Failed to load suppliers');
    } finally {
      setLoading(false);
    }
  };

  const openAdd = () => {
    setEditId(null);
    setForm({ name: '', email: '', phone: '', address: '' });
    setShowModal(true);
  };

  const openEdit = (supplier) => {
    setEditId(supplier._id || supplier.id);
    setForm({
      name: supplier.name || '',
      email: supplier.email || '',
      phone: supplier.phone || '',
      address: supplier.address || '',
    });
    setShowModal(true);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!form.name) {
      toast.error('Name is required');
      return;
    }
    setFormLoading(true);
    try {
      if (editId) {
        await api.updateSupplier(editId, form);
        toast.success('Supplier updated');
      } else {
        await api.createSupplier(form);
        toast.success('Supplier created');
      }
      setShowModal(false);
      fetchSuppliers();
    } catch (err) {
      toast.error(err.response?.data?.message || 'Operation failed');
    } finally {
      setFormLoading(false);
    }
  };

  const handleDelete = async (id) => {
    try {
      await api.deleteSupplier(id);
      toast.success('Supplier deleted');
      setDeleteConfirm(null);
      fetchSuppliers();
    } catch {
      toast.error('Failed to delete supplier');
    }
  };

  const updateForm = (field) => (e) => setForm({ ...form, [field]: e.target.value });

  if (loading) {
    return (
      <div className="space-y-6">
        <div className="skeleton h-8 w-40"></div>
        <div className="space-y-3">
          {[1, 2, 3].map((i) => (
            <div key={i} className="skeleton h-24 rounded-lg"></div>
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900">Suppliers</h1>
        <button
          onClick={openAdd}
          className="flex items-center gap-2 px-4 py-2.5 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 transition-colors"
        >
          <Plus className="w-4 h-4" />
          Add Supplier
        </button>
      </div>

      {suppliers.length === 0 ? (
        <div className="text-center py-16">
          <Truck className="w-12 h-12 text-gray-300 mx-auto mb-3" />
          <p className="text-gray-500">No suppliers yet</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {suppliers.map((supplier) => (
            <div key={supplier._id || supplier.id} className="bg-white border border-gray-200 rounded-lg p-5">
              <div className="flex items-start justify-between mb-3">
                <h3 className="font-semibold text-gray-900 capitalize">{supplier.name}</h3>
                <div className="flex items-center gap-1">
                  <button
                    onClick={() => openEdit(supplier)}
                    className="p-1.5 text-gray-400 hover:text-blue-600 hover:bg-blue-50 rounded-lg transition-colors"
                  >
                    <Edit3 className="w-4 h-4" />
                  </button>
                  <button
                    onClick={() => setDeleteConfirm(supplier._id || supplier.id)}
                    className="p-1.5 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded-lg transition-colors"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              </div>
              <div className="space-y-2 text-sm">
                {supplier.email && (
                  <div className="flex items-center gap-2 text-gray-600">
                    <Mail className="w-3.5 h-3.5 text-gray-400" />
                    {supplier.email}
                  </div>
                )}
                {supplier.phone && (
                  <div className="flex items-center gap-2 text-gray-600">
                    <Phone className="w-3.5 h-3.5 text-gray-400" />
                    {supplier.phone}
                  </div>
                )}
                {supplier.address && (
                  <div className="flex items-center gap-2 text-gray-600">
                    <MapPin className="w-3.5 h-3.5 text-gray-400" />
                    <span className="capitalize">{supplier.address}</span>
                  </div>
                )}
              </div>

              {/* Delete confirmation */}
              {deleteConfirm === (supplier._id || supplier.id) && (
                <div className="mt-4 pt-3 border-t border-gray-100 flex items-center gap-2">
                  <span className="text-xs text-red-600 font-medium">Delete?</span>
                  <button
                    onClick={() => handleDelete(supplier._id || supplier.id)}
                    className="px-3 py-1 bg-red-500 text-white text-xs font-medium rounded-lg hover:bg-red-600"
                  >
                    Yes
                  </button>
                  <button
                    onClick={() => setDeleteConfirm(null)}
                    className="px-3 py-1 text-xs text-gray-500 font-medium"
                  >
                    No
                  </button>
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {/* Add/Edit Modal */}
      {showModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 px-4">
          <div className="bg-white rounded-xl w-full max-w-md shadow-xl">
            <div className="flex items-center justify-between p-6 border-b border-gray-200">
              <h2 className="text-lg font-semibold text-gray-900">
                {editId ? 'Edit Supplier' : 'Add Supplier'}
              </h2>
              <button onClick={() => setShowModal(false)} className="text-gray-400 hover:text-gray-600">
                <X className="w-5 h-5" />
              </button>
            </div>
            <form onSubmit={handleSubmit} className="p-6 space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Name *</label>
                <input
                  value={form.name}
                  onChange={updateForm('name')}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="Supplier name"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Email</label>
                <input
                  type="email"
                  value={form.email}
                  onChange={updateForm('email')}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="supplier@example.com"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Phone</label>
                <input
                  type="tel"
                  maxLength="10"
                  value={form.phone}
                  onChange={updateForm('phone')}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="1234567890"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Address</label>
                <textarea
                  value={form.address}
                  onChange={updateForm('address')}
                  rows={2}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="Full address"
                />
              </div>
              <div className="flex justify-end gap-3 pt-2">
                <button type="button" onClick={() => setShowModal(false)} className="px-4 py-2 text-sm text-gray-600 font-medium">
                  Cancel
                </button>
                <button type="submit" disabled={formLoading} className="px-5 py-2 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 disabled:opacity-50">
                  {formLoading ? 'Saving...' : editId ? 'Update Supplier' : 'Create Supplier'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
