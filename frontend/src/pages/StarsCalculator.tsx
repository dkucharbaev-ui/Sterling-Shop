import React, { useState, useEffect } from 'react';
import { Star, Zap, ChevronRight } from 'lucide-react';
import { ru } from '../i18n/ru';
import { api } from '../api/client';
import { Product } from '../types';

interface StarsCalculatorProps {
  product: Product;
  onProceedToCheckout: (productId: string, quantity: number) => void;
  haptic: (style: 'light' | 'medium' | 'heavy') => void;
  isDark: boolean;
}

const PRESET_AMOUNTS = [50, 100, 250, 500, 1000, 2500, 5000];

export const StarsCalculator: React.FC<StarsCalculatorProps> = ({
  product,
  onProceedToCheckout,
  haptic,
  isDark,
}) => {
  const [quantity, setQuantity] = useState<number>(product.default_quantity || 100);
  const [calculatedPrice, setCalculatedPrice] = useState<number>(0);
  const [pricePerStar, setPricePerStar] = useState<number>(0);
  const [loading, setLoading] = useState<boolean>(false);

  useEffect(() => {
    let active = true;
    const fetchPrice = async () => {
      setLoading(true);
      try {
        const res = await api.calculateStars(quantity, 'RUB');
        if (active) {
          setCalculatedPrice(res.price);
          setPricePerStar(res.price_per_star);
        }
      } catch (e) {
        // Fallback local estimation
        if (active) {
          const approx = quantity * 2.15;
          setCalculatedPrice(approx);
          setPricePerStar(2.15);
        }
      } finally {
        if (active) setLoading(false);
      }
    };

    const timer = setTimeout(fetchPrice, 150);
    return () => {
      active = false;
      clearTimeout(timer);
    };
  }, [quantity]);

  const handleSelectPreset = (amount: number) => {
    haptic('light');
    setQuantity(amount);
  };

  return (
    <div className="space-y-6">
      {/* Title */}
      <div>
        <h2 className="text-xl font-bold flex items-center space-x-2">
          <Star className="w-5 h-5 text-amber-400 fill-amber-400" />
          <span>{ru.calculator.title}</span>
        </h2>
        <p className="text-xs text-slate-400 mt-1">{ru.calculator.subtitle}</p>
      </div>

      {/* Preset Buttons */}
      <div>
        <label className="text-xs font-semibold text-slate-400 uppercase tracking-wider block mb-2">
          Быстрый выбор
        </label>
        <div className="grid grid-cols-4 gap-2">
          {PRESET_AMOUNTS.map((amt) => {
            const isSelected = quantity === amt;
            return (
              <button
                key={amt}
                onClick={() => handleSelectPreset(amt)}
                className={`py-2.5 px-2 rounded-xl text-xs font-bold transition-all flex flex-col items-center ${
                  isSelected
                    ? 'bg-blue-600 text-white shadow-md shadow-blue-600/30 ring-2 ring-blue-400'
                    : isDark
                    ? 'bg-[#212d3b] text-slate-200 hover:bg-[#283747]'
                    : 'bg-white text-slate-700 hover:bg-slate-100 shadow-sm'
                }`}
              >
                <div className="flex items-center space-x-1">
                  <span>{amt}</span>
                  <Star className={`w-3 h-3 ${isSelected ? 'fill-white text-white' : 'fill-amber-400 text-amber-400'}`} />
                </div>
              </button>
            );
          })}
        </div>
      </div>

      {/* Custom Amount Input & Slider */}
      <div className={`p-4 rounded-2xl ${isDark ? 'bg-[#212d3b]' : 'bg-white shadow-sm'}`}>
        <label className="text-xs font-semibold text-slate-400 block mb-2">
          {ru.calculator.customAmount}
        </label>
        <div className="flex items-center space-x-3 mb-3">
          <input
            type="number"
            min={product.min_quantity || 1}
            max={product.max_quantity || 100000}
            value={quantity}
            onChange={(e) => {
              const val = Math.max(1, Math.min(100000, Number(e.target.value) || 1));
              setQuantity(val);
            }}
            className={`w-full text-2xl font-bold rounded-xl px-4 py-2 border outline-none ${
              isDark
                ? 'bg-[#18222d] border-slate-700 text-white focus:border-blue-500'
                : 'bg-slate-50 border-slate-200 text-slate-900 focus:border-blue-500'
            }`}
          />
          <span className="text-lg font-bold text-amber-500 flex items-center space-x-1">
            <Star className="w-5 h-5 fill-amber-500" />
          </span>
        </div>

        <input
          type="range"
          min={50}
          max={5000}
          step={50}
          value={quantity > 5000 ? 5000 : quantity}
          onChange={(e) => {
            haptic('light');
            setQuantity(Number(e.target.value));
          }}
          className="w-full accent-blue-500 cursor-pointer"
        />
        <div className="flex justify-between text-[11px] text-slate-400 mt-1">
          <span>50 Stars</span>
          <span>5 000 Stars</span>
        </div>
      </div>

      {/* Price Summary Card */}
      <div className={`p-4 rounded-2xl border ${isDark ? 'bg-[#212d3b]/70 border-slate-700' : 'bg-blue-50/50 border-blue-100'}`}>
        <div className="flex justify-between items-center text-xs text-slate-400 mb-1">
          <span>{ru.calculator.pricePerStar}</span>
          <span className="font-semibold text-slate-300">~{pricePerStar} ₽</span>
        </div>
        <div className="flex justify-between items-center text-lg font-extrabold">
          <span>{ru.calculator.totalAmount}</span>
          <span className="text-2xl text-blue-500">
            {loading ? '...' : `${calculatedPrice.toLocaleString('ru-RU')} ₽`}
          </span>
        </div>
      </div>

      {/* Action Button */}
      <button
        onClick={() => {
          haptic('medium');
          onProceedToCheckout(product.id, quantity);
        }}
        className="w-full py-4 rounded-xl bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 text-white font-bold text-base shadow-lg shadow-blue-500/25 flex items-center justify-center space-x-2 transition-all active:scale-[0.98]"
      >
        <span>Перейти к оформлению</span>
        <ChevronRight className="w-5 h-5" />
      </button>
    </div>
  );
};
