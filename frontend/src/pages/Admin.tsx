import React, { useState } from 'react';
import { Shield, TrendingUp, DollarSign, Wallet, Settings, Send, Search, RefreshCw, AlertTriangle } from 'lucide-react';
import { ru } from '../i18n/ru';
import { User } from '../types';

interface AdminProps {
  currentUser: User | null;
  isDark: boolean;
  haptic: (style: 'light' | 'medium' | 'heavy') => void;
}

export const Admin: React.FC<AdminProps> = ({ currentUser, isDark, haptic }) => {
  const [activeTab, setActiveTab] = useState<'stats' | 'orders' | 'broadcast' | 'settings'>('stats');
  const [broadcastText, setBroadcastText] = useState<string>('');
  const [broadcasting, setBroadcasting] = useState<boolean>(false);
  const [maintenance, setMaintenance] = useState<boolean>(false);
  const [marginStars, setMarginStars] = useState<number>(15);
  const [marginPremium, setMarginPremium] = useState<number>(18);

  if (!currentUser?.is_admin) {
    return (
      <div className={`p-8 rounded-2xl text-center ${isDark ? 'bg-[#212d3b]' : 'bg-white shadow-sm'}`}>
        <AlertTriangle className="w-12 h-12 text-amber-500 mx-auto mb-3" />
        <h3 className="text-lg font-bold">Доступ ограничен</h3>
        <p className="text-xs text-slate-400 mt-1">
          Этот раздел доступен только администраторам магазина.
        </p>
      </div>
    );
  }

  const handleSendBroadcast = async () => {
    if (!broadcastText.trim()) return;
    haptic('heavy');
    setBroadcasting(true);
    // Simulated broadcast trigger
    setTimeout(() => {
      setBroadcasting(false);
      setBroadcastText('');
      alert('Рассылка успешно запущена с лимитом 25 сообщений/сек!');
    }, 1000);
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-bold flex items-center space-x-2">
          <Shield className="w-5 h-5 text-red-500" />
          <span>{ru.admin.title}</span>
        </h2>
        <span className="text-xs font-semibold px-2.5 py-1 rounded-full bg-red-500/20 text-red-400 border border-red-500/30">
          Admin Mode
        </span>
      </div>

      {/* Tabs */}
      <div className="flex space-x-2 border-b border-slate-700/50 pb-2 overflow-x-auto text-xs font-bold">
        <button
          onClick={() => setActiveTab('stats')}
          className={`px-3 py-1.5 rounded-lg ${activeTab === 'stats' ? 'bg-blue-600 text-white' : 'text-slate-400'}`}
        >
          {ru.admin.dashboard}
        </button>
        <button
          onClick={() => setActiveTab('orders')}
          className={`px-3 py-1.5 rounded-lg ${activeTab === 'orders' ? 'bg-blue-600 text-white' : 'text-slate-400'}`}
        >
          {ru.admin.orders}
        </button>
        <button
          onClick={() => setActiveTab('settings')}
          className={`px-3 py-1.5 rounded-lg ${activeTab === 'settings' ? 'bg-blue-600 text-white' : 'text-slate-400'}`}
        >
          {ru.admin.settings}
        </button>
        <button
          onClick={() => setActiveTab('broadcast')}
          className={`px-3 py-1.5 rounded-lg ${activeTab === 'broadcast' ? 'bg-blue-600 text-white' : 'text-slate-400'}`}
        >
          {ru.admin.broadcast}
        </button>
      </div>

      {/* Stats Tab */}
      {activeTab === 'stats' && (
        <div className="space-y-4">
          <div className="grid grid-cols-2 gap-3">
            <div className={`p-4 rounded-2xl ${isDark ? 'bg-[#212d3b]' : 'bg-white shadow-sm'}`}>
              <div className="flex items-center space-x-2 text-slate-400 text-xs mb-1">
                <DollarSign className="w-4 h-4 text-emerald-400" />
                <span>{ru.admin.revenue}</span>
              </div>
              <span className="text-xl font-extrabold text-emerald-400">148 500 ₽</span>
            </div>

            <div className={`p-4 rounded-2xl ${isDark ? 'bg-[#212d3b]' : 'bg-white shadow-sm'}`}>
              <div className="flex items-center space-x-2 text-slate-400 text-xs mb-1">
                <TrendingUp className="w-4 h-4 text-blue-400" />
                <span>{ru.admin.profit}</span>
              </div>
              <span className="text-xl font-extrabold text-blue-400">22 275 ₽</span>
            </div>

            <div className={`p-4 rounded-2xl ${isDark ? 'bg-[#212d3b]' : 'bg-white shadow-sm'}`}>
              <div className="flex items-center space-x-2 text-slate-400 text-xs mb-1">
                <Wallet className="w-4 h-4 text-amber-400" />
                <span>{ru.admin.tonBalance}</span>
              </div>
              <span className="text-xl font-extrabold text-amber-400">42.85 TON</span>
            </div>

            <div className={`p-4 rounded-2xl ${isDark ? 'bg-[#212d3b]' : 'bg-white shadow-sm'}`}>
              <div className="flex items-center space-x-2 text-slate-400 text-xs mb-1">
                <RefreshCw className="w-4 h-4 text-purple-400" />
                <span>Всего заказов</span>
              </div>
              <span className="text-xl font-extrabold text-purple-400">312 шт.</span>
            </div>
          </div>
        </div>
      )}

      {/* Settings Tab */}
      {activeTab === 'settings' && (
        <div className={`p-5 rounded-2xl ${isDark ? 'bg-[#212d3b]' : 'bg-white shadow-sm'} space-y-4 text-xs`}>
          <div>
            <label className="font-semibold text-slate-300 block mb-1">Наценка на Stars (%)</label>
            <input
              type="number"
              value={marginStars}
              onChange={(e) => setMarginStars(Number(e.target.value))}
              className="w-full p-2.5 rounded-xl border border-slate-700 bg-black/20 font-bold"
            />
          </div>

          <div>
            <label className="font-semibold text-slate-300 block mb-1">Наценка на Premium (%)</label>
            <input
              type="number"
              value={marginPremium}
              onChange={(e) => setMarginPremium(Number(e.target.value))}
              className="w-full p-2.5 rounded-xl border border-slate-700 bg-black/20 font-bold"
            />
          </div>

          <div className="flex items-center justify-between pt-2 border-t border-slate-700/50">
            <div>
              <span className="font-bold block text-sm">{ru.admin.maintenance}</span>
              <span className="text-slate-400 text-[11px]">Блокирует создание новых заказов</span>
            </div>
            <input
              type="checkbox"
              checked={maintenance}
              onChange={(e) => setMaintenance(e.target.checked)}
              className="w-5 h-5 accent-red-600 rounded cursor-pointer"
            />
          </div>

          <button
            onClick={() => {
              haptic('medium');
              alert('Настройки сохранены!');
            }}
            className="w-full py-3 rounded-xl bg-blue-600 hover:bg-blue-500 text-white font-bold text-xs shadow-md shadow-blue-500/20"
          >
            {ru.admin.save}
          </button>
        </div>
      )}

      {/* Broadcast Tab */}
      {activeTab === 'broadcast' && (
        <div className={`p-5 rounded-2xl ${isDark ? 'bg-[#212d3b]' : 'bg-white shadow-sm'} space-y-3 text-xs`}>
          <div className="p-3 rounded-xl bg-blue-500/10 border border-blue-500/20 text-blue-300 text-[11px]">
            ⚡ Рассылка отправляется через aiogram фоновым пулом с автоматическим ограничением скорости (макс. 25 сообщ./сек) во избежание Telegram FloodWait.
          </div>

          <textarea
            rows={5}
            placeholder="Текст рассылки для всех пользователей (поддерживает Markdown/HTML)..."
            value={broadcastText}
            onChange={(e) => setBroadcastText(e.target.value)}
            className="w-full p-3 rounded-xl border border-slate-700 bg-black/20 outline-none text-slate-200"
          />

          <button
            onClick={handleSendBroadcast}
            disabled={broadcasting || !broadcastText.trim()}
            className="w-full py-3 rounded-xl bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 text-white font-bold flex items-center justify-center space-x-2"
          >
            <Send className="w-4 h-4" />
            <span>{broadcasting ? 'Отправка...' : 'Запустить рассылку'}</span>
          </button>
        </div>
      )}
    </div>
  );
};
