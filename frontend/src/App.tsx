import React, { useState, useEffect } from 'react';
import { ru } from './i18n/ru';
import { useTelegram } from './hooks/useTelegram';
import { api } from './api/client';
import { Category, Product, User } from './types';
import { StarsCalculator } from './pages/StarsCalculator';
import { PremiumPlans } from './pages/PremiumPlans';
import { Checkout } from './pages/Checkout';
import { Orders } from './pages/Orders';
import { Support } from './pages/Support';
import { Admin } from './pages/Admin';

import {
  Star,
  ShieldCheck,
  Zap,
  ShoppingCart,
  MessageCircle,
  RefreshCw,
  Shield,
  HelpCircle,
  Gift,
} from 'lucide-react';

export default function App() {
  const { tg, initData, isDark, haptic, hapticNotification, openLink } = useTelegram();

  const [activeTab, setActiveTab] = useState<'home' | 'stars' | 'premium' | 'checkout' | 'orders' | 'support' | 'admin'>('home');
  const [currentUser, setCurrentUser] = useState<User | null>(null);
  const [categories, setCategories] = useState<Category[]>([]);
  const [selectedProduct, setSelectedProduct] = useState<Product | null>(null);
  const [checkoutQuantity, setCheckoutQuantity] = useState<number>(100);

  // Authenticate user via initData and load catalog
  useEffect(() => {
    const initApp = async () => {
      try {
        if (initData) {
          const authData = await api.authenticate(initData);
          setCurrentUser(authData.user);
        } else {
          // Fallback demo user for browser testing outside Telegram WebApp
          setCurrentUser({
            id: 12345678,
            first_name: 'Демо',
            username: 'demo_user',
            is_premium: false,
            is_blocked: false,
            is_admin: true,
          });
        }

        const cats = await api.getCatalog();
        setCategories(cats);
      } catch (e) {
        console.warn('Initialization notice:', e);
      }
    };

    initApp();
  }, [initData]);

  // Extract products
  const starsCategory = categories.find((c) => c.slug === 'stars');
  const premiumCategory = categories.find((c) => c.slug === 'premium');

  const defaultStarsProduct: Product = starsCategory?.products?.[0] || {
    id: 'mock-stars',
    sku: 'stars-custom',
    name: 'Telegram Stars',
    product_type: 'STARS_CUSTOM',
    base_price_ton: 0.0135,
    min_quantity: 50,
    max_quantity: 100000,
    default_quantity: 100,
    is_active: true,
    sort_order: 1,
    estimated_price_rub: 215,
  };

  const defaultPremiumProducts: Product[] = premiumCategory?.products?.length
    ? premiumCategory.products
    : [
        {
          id: 'mock-prem-3',
          sku: 'premium-3',
          name: 'Telegram Premium 3 мес.',
          product_type: 'PREMIUM_MONTHS',
          base_price_ton: 2.2,
          default_quantity: 3,
          is_active: true,
          sort_order: 1,
          estimated_price_rub: 1190,
        },
        {
          id: 'mock-prem-6',
          sku: 'premium-6',
          name: 'Telegram Premium 6 мес.',
          product_type: 'PREMIUM_MONTHS',
          base_price_ton: 3.9,
          default_quantity: 6,
          is_active: true,
          sort_order: 2,
          estimated_price_rub: 1990,
        },
        {
          id: 'mock-prem-12',
          sku: 'premium-12',
          name: 'Telegram Premium 12 мес.',
          product_type: 'PREMIUM_MONTHS',
          base_price_ton: 6.9,
          default_quantity: 12,
          is_active: true,
          sort_order: 3,
          estimated_price_rub: 3490,
        },
      ];

  const handleStartStarsCheckout = (productId: string, quantity: number) => {
    setSelectedProduct(defaultStarsProduct);
    setCheckoutQuantity(quantity);
    setActiveTab('checkout');
  };

  const handleStartPremiumCheckout = (productId: string, months: number) => {
    const prod = defaultPremiumProducts.find((p) => p.id === productId) || defaultPremiumProducts[0];
    setSelectedProduct(prod);
    setCheckoutQuantity(months);
    setActiveTab('checkout');
  };

  return (
    <div
      className={`min-h-screen ${
        isDark ? 'bg-[#18222d] text-white' : 'bg-[#f4f4f5] text-slate-900'
      } p-4 pb-24 font-sans select-none`}
    >
      {/* Tab: Home */}
      {activeTab === 'home' && (
        <div className="space-y-6">
          {/* Hero Banner */}
          <div className="relative overflow-hidden rounded-3xl bg-gradient-to-r from-blue-600 via-indigo-600 to-purple-600 p-6 text-white shadow-xl">
            <div className="relative z-10">
              <div className="inline-flex items-center space-x-1.5 px-3 py-1 rounded-full bg-white/10 backdrop-blur-md text-amber-300 font-semibold text-xs mb-3">
                <Zap className="w-3.5 h-3.5 fill-amber-300" />
                <span>Официальная выдача Fragment / TON</span>
              </div>
              <h1 className="text-2xl font-black tracking-tight">{ru.home.bannerTitle}</h1>
              <p className="mt-1 text-xs text-blue-100 max-w-xs">{ru.home.bannerSubtitle}</p>
            </div>
            <div className="absolute -right-6 -bottom-6 w-36 h-36 bg-white/10 rounded-full blur-2xl pointer-events-none" />
          </div>

          {/* Quick Categories */}
          <div>
            <h2 className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-3">
              {ru.home.categoriesTitle}
            </h2>
            <div className="grid grid-cols-2 gap-3">
              <button
                onClick={() => {
                  haptic('light');
                  setActiveTab('stars');
                }}
                className={`flex flex-col items-start p-5 rounded-2xl transition-all border ${
                  isDark
                    ? 'bg-[#212d3b] border-slate-800 hover:border-amber-500/50'
                    : 'bg-white border-slate-200 shadow-sm hover:border-amber-500/50'
                }`}
              >
                <div className="w-12 h-12 rounded-2xl bg-amber-500/20 flex items-center justify-center mb-3 text-amber-400">
                  <Star className="w-6 h-6 fill-amber-400" />
                </div>
                <span className="font-bold text-base">{ru.home.starsTitle}</span>
                <span className="text-xs text-slate-400 mt-1">От 50 до 100 000 звёзд</span>
              </button>

              <button
                onClick={() => {
                  haptic('light');
                  setActiveTab('premium');
                }}
                className={`flex flex-col items-start p-5 rounded-2xl transition-all border ${
                  isDark
                    ? 'bg-[#212d3b] border-slate-800 hover:border-purple-500/50'
                    : 'bg-white border-slate-200 shadow-sm hover:border-purple-500/50'
                }`}
              >
                <div className="w-12 h-12 rounded-2xl bg-purple-500/20 flex items-center justify-center mb-3 text-purple-400">
                  <ShieldCheck className="w-6 h-6" />
                </div>
                <span className="font-bold text-base">{ru.home.premiumTitle}</span>
                <span className="text-xs text-slate-400 mt-1">3, 6 или 12 месяцев</span>
              </button>
            </div>
          </div>

          {/* Guarantee Perks */}
          <div className={`p-4 rounded-2xl ${isDark ? 'bg-[#212d3b]' : 'bg-white shadow-sm'}`}>
            <h3 className="font-bold text-xs flex items-center space-x-2 mb-2 text-slate-300">
              <ShieldCheck className="w-4 h-4 text-emerald-400" />
              <span>Безопасная и быстрая доставка</span>
            </h3>
            <p className="text-xs text-slate-400 leading-relaxed">
              Все покупки отправляются напрямую через блокчейн TON и защищённый шлюз. Никаких паролей — только ваш @username.
            </p>
          </div>
        </div>
      )}

      {/* Tab: Stars */}
      {activeTab === 'stars' && (
        <StarsCalculator
          product={defaultStarsProduct}
          onProceedToCheckout={handleStartStarsCheckout}
          haptic={haptic}
          isDark={isDark}
        />
      )}

      {/* Tab: Premium */}
      {activeTab === 'premium' && (
        <PremiumPlans
          products={defaultPremiumProducts}
          onSelectPlan={handleStartPremiumCheckout}
          haptic={haptic}
          isDark={isDark}
        />
      )}

      {/* Tab: Checkout */}
      {activeTab === 'checkout' && selectedProduct && (
        <Checkout
          product={selectedProduct}
          quantity={checkoutQuantity}
          currentUser={currentUser}
          onBack={() => setActiveTab('home')}
          onOrderSuccess={() => setActiveTab('orders')}
          haptic={haptic}
          hapticNotification={hapticNotification}
          openLink={openLink}
          isDark={isDark}
        />
      )}

      {/* Tab: Orders */}
      {activeTab === 'orders' && (
        <Orders
          onRepeatOrder={(prodId, qty) => {
            const p = defaultPremiumProducts.find((x) => x.id === prodId) || defaultStarsProduct;
            setSelectedProduct(p);
            setCheckoutQuantity(qty);
            setActiveTab('checkout');
          }}
          haptic={haptic}
          openLink={openLink}
          isDark={isDark}
        />
      )}

      {/* Tab: Support */}
      {activeTab === 'support' && <Support isDark={isDark} haptic={haptic} />}

      {/* Tab: Admin */}
      {activeTab === 'admin' && (
        <Admin currentUser={currentUser} isDark={isDark} haptic={haptic} />
      )}

      {/* Persistent Bottom Floating Navigation Bar */}
      <nav
        className={`fixed bottom-0 left-0 right-0 py-2.5 px-4 border-t flex justify-around items-center ${
          isDark ? 'bg-[#18222d]/95 border-slate-800' : 'bg-white/95 border-slate-200'
        } backdrop-blur-lg z-50`}
      >
        <button
          onClick={() => {
            haptic('light');
            setActiveTab('home');
          }}
          className={`flex flex-col items-center text-[10px] font-bold ${
            activeTab === 'home' ? 'text-blue-500' : 'text-slate-400'
          }`}
        >
          <ShoppingCart className="w-5 h-5 mb-1" />
          <span>Витрина</span>
        </button>

        <button
          onClick={() => {
            haptic('light');
            setActiveTab('stars');
          }}
          className={`flex flex-col items-center text-[10px] font-bold ${
            activeTab === 'stars' ? 'text-amber-400' : 'text-slate-400'
          }`}
        >
          <Star className="w-5 h-5 mb-1" />
          <span>Stars</span>
        </button>

        <button
          onClick={() => {
            haptic('light');
            setActiveTab('premium');
          }}
          className={`flex flex-col items-center text-[10px] font-bold ${
            activeTab === 'premium' ? 'text-purple-400' : 'text-slate-400'
          }`}
        >
          <ShieldCheck className="w-5 h-5 mb-1" />
          <span>Premium</span>
        </button>

        <button
          onClick={() => {
            haptic('light');
            setActiveTab('orders');
          }}
          className={`flex flex-col items-center text-[10px] font-bold ${
            activeTab === 'orders' ? 'text-blue-500' : 'text-slate-400'
          }`}
        >
          <RefreshCw className="w-5 h-5 mb-1" />
          <span>Заказы</span>
        </button>

        <button
          onClick={() => {
            haptic('light');
            setActiveTab('support');
          }}
          className={`flex flex-col items-center text-[10px] font-bold ${
            activeTab === 'support' ? 'text-blue-500' : 'text-slate-400'
          }`}
        >
          <HelpCircle className="w-5 h-5 mb-1" />
          <span>Инфо</span>
        </button>

        {currentUser?.is_admin && (
          <button
            onClick={() => {
              haptic('medium');
              setActiveTab('admin');
            }}
            className={`flex flex-col items-center text-[10px] font-bold ${
              activeTab === 'admin' ? 'text-red-500' : 'text-slate-400'
            }`}
          >
            <Shield className="w-5 h-5 mb-1" />
            <span>Админ</span>
          </button>
        )}
      </nav>
    </div>
  );
}
