import { NavLink, useNavigate } from 'react-router-dom';
import { Package, LayoutDashboard, Box, Truck, LogOut } from 'lucide-react';
import { useAuth } from '../auth';

export default function Navbar() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  const linkClass = ({ isActive }) =>
    `flex items-center gap-1.5 px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
      isActive
        ? 'text-blue-600 bg-blue-50'
        : 'text-gray-600 hover:text-gray-900 hover:bg-gray-50'
    }`;

  return (
    <nav className="fixed top-0 left-0 right-0 z-50 bg-white border-b border-gray-200">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          <div className="flex items-center gap-2">
            <Package className="w-7 h-7 text-blue-600" />
            <span className="text-xl font-bold text-blue-600">SmartInventory</span>
          </div>

          <div className="flex items-center gap-1">
            <NavLink to="/" end className={linkClass}>
              <LayoutDashboard className="w-4 h-4" />
              Dashboard
            </NavLink>
            <NavLink to="/products" className={linkClass}>
              <Box className="w-4 h-4" />
              Products
            </NavLink>
            <NavLink to="/suppliers" className={linkClass}>
              <Truck className="w-4 h-4" />
              Suppliers
            </NavLink>
          </div>

          <div className="flex items-center gap-4">
            <span className="text-sm text-gray-600">
              Hi, <span className="font-medium text-gray-900">{user?.username || 'User'}</span>
            </span>
            <button
              onClick={handleLogout}
              className="flex items-center gap-1.5 px-3 py-2 text-sm text-gray-600 hover:text-red-600 hover:bg-red-50 rounded-lg transition-colors"
            >
              <LogOut className="w-4 h-4" />
              Logout
            </button>
          </div>
        </div>
      </div>
    </nav>
  );
}
