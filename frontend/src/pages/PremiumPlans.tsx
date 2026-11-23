import React from 'react';
import { ShieldCheck, Check, Sparkles, ChevronRight } from 'lucide-react';
import { ru } from '../i18n/ru';
import { Product } from '../types';

interface PremiumPlansProps {
  products: Product[];
  onSelectPlan: (productId: string, months: number) => void;
  haptic: (style: 'light' | 'medium' | 'heavy') => void;
  isDark: boolean;
}

export const PremiumPlans: React.FC<PremiumPlansProps> = ({
  products,
  onSelectPlan,
  haptic,
  isDark,
}) => {
  const sortedProducts = [...products].sort((a, b) => a.default_quantity - b.default_quantity);

  const getPlanDiscount = (months: number) => {
    if (months === 6) return 'Экономия 15%';
    if (months === 12) return 'Экономия 35% 🔥';
    return null;
  };

  return (
    <div className="space-y-6">
      {/* Title */}
      <div>
        <h2 className="text-xl font-bold flex items-center space-x-2">
          <ShieldCheck className="w-5 h-5 text-purple-400" />
          <span>{ru.premium.title}</span>
        </h2>
        <p className="text-xs text-slate-400 mt-1">{ru.premium.subtitle}</p>
      </div>

      {/* Plans List */}
      <div className="space-y-3">
        {sortedProducts.map((p) => {
          const months = p.default_quantity;
          const discount = getPlanDiscount(months);
          const isBest = months === 12;

          return (
            <div
              key={p.id}
              onClick={() => {
                haptic('medium');
                onSelectPlan(p.id, months);
              }}
              className={`relative p-5 rounded-2xl cursor-pointer transition-all border ${
                isBest
                  ? 'border-purple-500/60 ring-2 ring-purple-500/30'
                  : isDark
                  ? 'border-slate-800'
                  : 'border-slate-200'
              } ${
                isDark
                  ? 'bg-[#212d3b] hover:bg-[#283747]'
                  : 'bg-white hover:bg-slate-50 shadow-sm'
              }`}
            >
              {discount && (
                <div className="absolute top-3 right-3 px-2 py-0.5 rounded-full text-[10px] font-bold bg-purple-500/20 text-purple-400 border border-purple-500/30">
                  {discount}
                </div>
              )}

              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center space-x-2">
                  <div className="w-8 h-8 rounded-lg bg-purple-500/20 flex items-center justify-center text-purple-400">
                    <Sparkles className="w-4 h-4" />
                  </div>
                  <div>
                    <h3 className="font-bold text-base">{p.name}</h3>
                    <span className="text-xs text-slate-400">{months} {ru.common.months}</span>
                  </div>
                </div>
              </div>

              <div className="flex items-end justify-between mt-3 pt-3 border-t border-slate-700/50">
                <div>
                  <span className="text-xs text-slate-400 block">Стоимость:</span>
                  <span className="text-xl font-extrabold text-purple-400">
                    {p.estimated_price_rub ? `${p.estimated_price_rub.toLocaleString('ru-RU')} ₽` : 'Рассчитать'}
                  </span>
                </div>
                <button className="px-4 py-2 rounded-xl bg-purple-600 hover:bg-purple-500 text-white font-bold text-xs flex items-center space-x-1 shadow-md shadow-purple-500/20">
                  <span>Выбрать</span>
                  <ChevronRight className="w-3.5 h-3.5" />
                </button>
              </div>
            </div>
          );
        })}
      </div>

      {/* Telegram Premium Perks List */}
      <div className={`p-4 rounded-2xl ${isDark ? 'bg-[#212d3b]' : 'bg-white shadow-sm'}`}>
        <h4 className="font-semibold text-xs text-slate-400 uppercase tracking-wider mb-3">
          Что входит в подписку:
        </h4>
        <ul className="space-y-2 text-xs">
          {[
            'Удвоенные лимиты (каналы, чаты, папки)',
            'Загрузка файлов до 4 ГБ',
            'Максимальная скорость скачивания',
            'Расшифровка голосовых и видеосообщений',
            'Эксклюзивные реакции и анимированные эмодзи',
            'Активный значок Premium в профиле',
          ].map((perk, idx) => (
            <li key={idx} className="flex items-center space-x-2 text-slate-300">
              <Check className="w-4 h-4 text-emerald-400 shrink-0" />
              <span>{perk}</span>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
};
