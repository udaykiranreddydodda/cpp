import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { Package, DollarSign, AlertTriangle, ArrowUpDown, Bell, ArrowDownCircle, ArrowUpCircle } from 'lucide-react';
import * as api from '../api';
import toast from 'react-hot-toast';

export default function Dashboard() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [subEmail, setSubEmail] = useState('');
  const [subLoading, setSubLoading] = useState(false);
  const [subCount, setSubCount] = useState(0);

  useEffect(() => {
    fetchDashboard();
    fetchSubCount();
  }, []);

  const fetchDashboard = async () => {
    try {
      const res = await api.getDashboard();
      setData(res.data);
    } catch (err) {
      toast.error('Failed to load dashboard');
    } finally {
      setLoading(false);
    }
  };

  const fetchSubCount = async () => {
    try {
      const res = await api.getSubscriberCount();
      setSubCount(res.data.count || 0);
    } catch {
      // ignore
    }
  };

  const handleSubscribe = async (e) => {
    e.preventDefault();
    if (!subEmail) return;
    setSubLoading(true);
    try {
      await api.subscribe({ email: subEmail });
      toast.success('Subscribed to notifications!');
      setSubEmail('');
      fetchSubCount();
    } catch (err) {
      toast.error(err.response?.data?.message || 'Subscription failed');
    } finally {
      setSubLoading(false);
    }
  };

  const today = new Date().toLocaleDateString('en-US', {
    weekday: 'long', year: 'numeric', month: 'long', day: 'numeric',
  });

  if (loading) {
    return (
      <div className="space-y-6">
        <div className="skeleton h-8 w-48"></div>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="skeleton h-28 rounded-lg"></div>
          ))}
        </div>
        <div className="skeleton h-64 rounded-lg"></div>
      </div>
    );
  }

  const stats = [
    {
      label: 'Total Products',
      value: data?.totalProducts ?? 0,
      icon: Package,
      color: 'text-blue-600',
      bg: 'bg-blue-50',
    },
    {
      label: 'Total Value',
      value: `$${(data?.totalValue ?? 0).toLocaleString()}`,
      icon: DollarSign,
      color: 'text-green-600',
      bg: 'bg-green-50',
    },
    {
      label: 'Low Stock',
      value: data?.lowStockCount ?? 0,
      icon: AlertTriangle,
      color: 'text-amber-600',
      bg: 'bg-amber-50',
    },
    {
      label: 'Recent Movements',
      value: data?.recentMovements?.length ?? 0,
      icon: ArrowUpDown,
      color: 'text-purple-600',
      bg: 'bg-purple-50',
    },
  ];

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Dashboard</h1>
        <p className="text-sm text-gray-500 mt-1">{today}</p>
      </div>

      {/* Stat cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {stats.map((stat) => (
          <div key={stat.label} className="bg-white border border-gray-200 rounded-lg p-5">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-500">{stat.label}</p>
                <p className="text-2xl font-bold text-gray-900 mt-1">{stat.value}</p>
              </div>
              <div className={`w-10 h-10 ${stat.bg} rounded-lg flex items-center justify-center`}>
                <stat.icon className={`w-5 h-5 ${stat.color}`} />
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Low stock alerts */}
      {data?.lowStockProducts && data.lowStockProducts.length > 0 && (
        <div>
          <h2 className="text-lg font-semibold text-gray-900 mb-3">Low Stock Alerts</h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
            {data.lowStockProducts.map((product) => (
              <Link
                key={product._id || product.id}
                to={`/products/${product._id || product.id}`}
                className="flex items-center gap-3 bg-amber-50 border border-amber-200 rounded-lg p-4 hover:bg-amber-100 transition-colors"
              >
                <AlertTriangle className="w-5 h-5 text-amber-600 flex-shrink-0" />
                <div className="min-w-0">
                  <p className="text-sm font-medium text-gray-900 truncate">{product.name}</p>
                  <p className="text-xs text-amber-700">
                    Stock: {product.currentStock} / Min: {product.minStock}
                  </p>
                </div>
              </Link>
            ))}
          </div>
        </div>
      )}

      {/* Recent activity */}
      <div>
        <h2 className="text-lg font-semibold text-gray-900 mb-3">Recent Activity</h2>
        <div className="bg-white border border-gray-200 rounded-lg overflow-hidden">
          {data?.recentMovements && data.recentMovements.length > 0 ? (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-gray-100 bg-gray-50">
                    <th className="text-left py-3 px-4 font-medium text-gray-600">Date</th>
                    <th className="text-left py-3 px-4 font-medium text-gray-600">Product</th>
                    <th className="text-left py-3 px-4 font-medium text-gray-600">Type</th>
                    <th className="text-left py-3 px-4 font-medium text-gray-600">Qty</th>
                    <th className="text-left py-3 px-4 font-medium text-gray-600">Reference</th>
                  </tr>
                </thead>
                <tbody>
                  {data.recentMovements.slice(0, 10).map((mov, i) => (
                    <tr key={i} className="border-b border-gray-50 hover:bg-gray-50">
                      <td className="py-3 px-4 text-gray-600">
                        {new Date(mov.date || mov.createdAt).toLocaleDateString()}
                      </td>
                      <td className="py-3 px-4 font-medium text-gray-900">
                        {mov.productName || mov.product?.name || '-'}
                      </td>
                      <td className="py-3 px-4">
                        <span className={`inline-flex items-center gap-1 text-xs font-medium px-2 py-0.5 rounded-full ${
                          mov.type === 'intake' || mov.type === 'Intake'
                            ? 'bg-green-100 text-green-700'
                            : 'bg-red-100 text-red-700'
                        }`}>
                          {mov.type === 'intake' || mov.type === 'Intake' ? (
                            <ArrowDownCircle className="w-3 h-3" />
                          ) : (
                            <ArrowUpCircle className="w-3 h-3" />
                          )}
                          {mov.type}
                        </span>
                      </td>
                      <td className="py-3 px-4 font-medium text-gray-900">{mov.quantity}</td>
                      <td className="py-3 px-4 text-gray-500">{mov.reference || '-'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="py-12 text-center text-gray-400">
              <ArrowUpDown className="w-8 h-8 mx-auto mb-2 opacity-50" />
              <p>No recent activity</p>
            </div>
          )}
        </div>
      </div>

      {/* Subscribe section */}
      <div className="bg-white border border-gray-200 rounded-lg p-6">
        <div className="flex items-center gap-3 mb-3">
          <div className="w-10 h-10 bg-blue-50 rounded-lg flex items-center justify-center">
            <Bell className="w-5 h-5 text-blue-600" />
          </div>
          <div>
            <h3 className="text-base font-semibold text-gray-900">Stock Notifications</h3>
            <p className="text-sm text-gray-500">Get notified about low stock alerts</p>
          </div>
        </div>
        <form onSubmit={handleSubscribe} className="flex gap-3 mt-4">
          <input
            type="email"
            value={subEmail}
            onChange={(e) => setSubEmail(e.target.value)}
            placeholder="Enter your email"
            className="flex-1 px-4 py-2.5 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
          />
          <button
            type="submit"
            disabled={subLoading}
            className="px-5 py-2.5 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-50"
          >
            {subLoading ? 'Subscribing...' : 'Subscribe'}
          </button>
        </form>
        {subCount > 0 && (
          <p className="text-xs text-gray-400 mt-2">{subCount} subscriber{subCount !== 1 ? 's' : ''}</p>
        )}
      </div>
    </div>
  );
}
