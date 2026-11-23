import React, { useState, useEffect } from 'react';
import { ShieldCheck, User as UserIcon, Gift, CheckCircle2, AlertCircle, CreditCard, ChevronLeft, Loader2 } from 'lucide-react';
import { ru } from '../i18n/ru';
import { api } from '../api/client';
import { PaymentProvider, Product, User } from '../types';

interface CheckoutProps {
  product: Product;
  quantity: number;
  currentUser: User | null;
  onBack: () => void;
  onOrderSuccess: (orderId: string) => void;
  haptic: (style: 'light' | 'medium' | 'heavy') => void;
  hapticNotification: (type: 'error' | 'success' | 'warning') => void;
  openLink: (url: string) => void;
  isDark: boolean;
}

export const Checkout: React.FC<CheckoutProps> = ({
  product,
  quantity,
  currentUser,
  onBack,
  onOrderSuccess,
  haptic,
  hapticNotification,
  openLink,
  isDark,
}) => {
  const [recipientMode, setRecipientMode] = useState<'self' | 'gift'>('self');
  const [recipientUsername, setRecipientUsername] = useState<string>(currentUser?.username || '');
  const [validating, setValidating] = useState<boolean>(false);
  const [validationError, setValidationError] = useState<string | null>(null);
  const [isValidated, setIsValidated] = useState<boolean>(false);

  const [paymentProvider, setPaymentProvider] = useState<PaymentProvider>('CRYPTOBOT');
  const [submitting, setSubmitting] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const isPremiumProduct = product.product_type === 'PREMIUM_MONTHS';

  // Recipient validation effect
  useEffect(() => {
    let active = true;
    const validate = async () => {
      const clean = recipientUsername.trim().replace(/^@/, '');
      if (clean.length < 5) {
        setIsValidated(false);
        setValidationError(clean.length > 0 ? 'Минимум 5 символов' : null);
        return;
      }

      setValidating(true);
      setValidationError(null);
      try {
        const res = await api.validateRecipient(clean, product.id);
        if (active) {
          if (!res.is_valid) {
            setValidationError(res.error_message || 'Пользователь не найден');
            setIsValidated(false);
          } else if (res.has_active_premium && isPremiumProduct) {
            setValidationError('На этом аккаунте уже активна подписка Premium!');
            setIsValidated(false);
          } else {
            setValidationError(null);
            setIsValidated(true);
          }
        }
      } catch (e: any) {
        if (active) {
          setValidationError(e.message || 'Ошибка проверки username');
          setIsValidated(false);
        }
      } finally {
        if (active) setValidating(false);
      }
    };

    const timer = setTimeout(validate, 300);
    return () => {
      active = false;
      clearTimeout(timer);
    };
  }, [recipientUsername, product.id, isPremiumProduct]);

  const handleSelectSelf = () => {
    haptic('light');
    setRecipientMode('self');
    setRecipientUsername(currentUser?.username || '');
  };

  const handleSelectGift = () => {
    haptic('light');
    setRecipientMode('gift');
    setRecipientUsername('');
    setIsValidated(false);
  };

  const handleCreateOrder = async () => {
    if (!isValidated && !recipientUsername) {
      setError('Укажите корректный @username получателя');
      hapticNotification('error');
      return;
    }

    setSubmitting(true);
    setError(null);
    haptic('heavy');

    try {
      const order = await api.createOrder({
        product_id: product.id,
        quantity,
        recipient_username: recipientUsername.trim().replace(/^@/, ''),
        payment_provider: paymentProvider,
        currency: 'RUB',
        is_gift: recipientMode === 'gift',
      });

      hapticNotification('success');

      // If payment URL returned immediately, open it
      if (order.payment_url) {
        openLink(order.payment_url);
      }
      onOrderSuccess(order.id);
    } catch (e: any) {
      hapticNotification('error');
      setError(e.message || 'Не удалось создать заказ');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Back button & Title */}
      <div className="flex items-center space-x-3">
        <button
          onClick={() => {
            haptic('light');
            onBack();
          }}
          className={`p-2 rounded-xl ${isDark ? 'bg-[#212d3b] hover:bg-[#283747]' : 'bg-white hover:bg-slate-100 shadow-sm'}`}
        >
          <ChevronLeft className="w-5 h-5" />
        </button>
        <h2 className="text-xl font-bold">{ru.checkout.title}</h2>
      </div>

      {/* Recipient Selection */}
      <div className={`p-5 rounded-2xl ${isDark ? 'bg-[#212d3b]' : 'bg-white shadow-sm'} space-y-4`}>
        <h3 className="font-bold text-sm flex items-center space-x-2">
          <UserIcon className="w-4 h-4 text-blue-400" />
          <span>{ru.checkout.recipientTitle}</span>
        </h3>

        {/* Self vs Gift toggle */}
        <div className="grid grid-cols-2 gap-2 p-1 bg-black/10 rounded-xl">
          <button
            onClick={handleSelectSelf}
            className={`py-2 rounded-lg text-xs font-bold transition-all flex items-center justify-center space-x-1 ${
              recipientMode === 'self'
                ? 'bg-blue-600 text-white shadow'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            <UserIcon className="w-3.5 h-3.5" />
            <span>{ru.common.self}</span>
          </button>
          <button
            onClick={handleSelectGift}
            className={`py-2 rounded-lg text-xs font-bold transition-all flex items-center justify-center space-x-1 ${
              recipientMode === 'gift'
                ? 'bg-blue-600 text-white shadow'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            <Gift className="w-3.5 h-3.5" />
            <span>{ru.common.gift}</span>
          </button>
        </div>

        {/* Username input */}
        <div>
          <label className="text-xs text-slate-400 block mb-1.5">{ru.checkout.recipientHint}</label>
          <div className="relative">
            <span className="absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-400 font-bold">@</span>
            <input
              type="text"
              placeholder="username"
              value={recipientUsername}
              disabled={recipientMode === 'self' && !!currentUser?.username}
              onChange={(e) => setRecipientUsername(e.target.value)}
              className={`w-full pl-8 pr-10 py-3 rounded-xl border outline-none text-sm font-semibold ${
                validationError
                  ? 'border-red-500/80 bg-red-500/10'
                  : isValidated
                  ? 'border-emerald-500/80 bg-emerald-500/10'
                  : isDark
                  ? 'bg-[#18222d] border-slate-700'
                  : 'bg-slate-50 border-slate-200'
              }`}
            />
            <div className="absolute right-3.5 top-1/2 -translate-y-1/2">
              {validating && <Loader2 className="w-4 h-4 text-blue-400 animate-spin" />}
              {isValidated && !validating && <CheckCircle2 className="w-4 h-4 text-emerald-400" />}
              {validationError && !validating && <AlertCircle className="w-4 h-4 text-red-400" />}
            </div>
          </div>
          {validationError && (
            <p className="text-xs text-red-400 mt-1.5 flex items-center space-x-1">
              <span>{validationError}</span>
            </p>
          )}
          {isValidated && (
            <p className="text-xs text-emerald-400 mt-1.5 flex items-center space-x-1">
              <span>{ru.checkout.usernameValid}</span>
            </p>
          )}
        </div>
      </div>

      {/* Payment Provider Selection */}
      <div className={`p-5 rounded-2xl ${isDark ? 'bg-[#212d3b]' : 'bg-white shadow-sm'} space-y-3`}>
        <h3 className="font-bold text-sm flex items-center space-x-2">
          <CreditCard className="w-4 h-4 text-blue-400" />
          <span>{ru.checkout.paymentMethodTitle}</span>
        </h3>

        {/* CryptoBot option */}
        <div
          onClick={() => {
            haptic('light');
            setPaymentProvider('CRYPTOBOT');
          }}
          className={`p-3.5 rounded-xl border cursor-pointer transition-all flex items-center justify-between ${
            paymentProvider === 'CRYPTOBOT'
              ? 'border-blue-500 bg-blue-500/10'
              : isDark
              ? 'border-slate-800 hover:border-slate-700'
              : 'border-slate-200'
          }`}
        >
          <div>
            <h4 className="font-bold text-sm">{ru.checkout.cryptobotName}</h4>
            <span className="text-xs text-slate-400">{ru.checkout.cryptobotDesc}</span>
          </div>
          <div
            className={`w-5 h-5 rounded-full border-2 flex items-center justify-center ${
              paymentProvider === 'CRYPTOBOT' ? 'border-blue-500 bg-blue-500' : 'border-slate-600'
            }`}
          >
            {paymentProvider === 'CRYPTOBOT' && <div className="w-2 h-2 rounded-full bg-white" />}
          </div>
        </div>

        {/* Lava Pay option */}
        <div
          onClick={() => {
            haptic('light');
            setPaymentProvider('LAVAPAY');
          }}
          className={`p-3.5 rounded-xl border cursor-pointer transition-all flex items-center justify-between ${
            paymentProvider === 'LAVAPAY'
              ? 'border-blue-500 bg-blue-500/10'
              : isDark
              ? 'border-slate-800 hover:border-slate-700'
              : 'border-slate-200'
          }`}
        >
          <div>
            <h4 className="font-bold text-sm">{ru.checkout.lavapayName}</h4>
            <span className="text-xs text-slate-400">{ru.checkout.lavapayDesc}</span>
          </div>
          <div
            className={`w-5 h-5 rounded-full border-2 flex items-center justify-center ${
              paymentProvider === 'LAVAPAY' ? 'border-blue-500 bg-blue-500' : 'border-slate-600'
            }`}
          >
            {paymentProvider === 'LAVAPAY' && <div className="w-2 h-2 rounded-full bg-white" />}
          </div>
        </div>
      </div>

      {/* Order Summary & Notice */}
      <div className={`p-5 rounded-2xl ${isDark ? 'bg-[#212d3b]' : 'bg-white shadow-sm'} space-y-2`}>
        <h4 className="font-semibold text-xs text-slate-400 uppercase tracking-wider mb-2">
          {ru.checkout.orderSummary}
        </h4>
        <div className="flex justify-between text-xs">
          <span className="text-slate-400">{ru.checkout.item}</span>
          <span className="font-bold">{product.name} ({quantity} шт.)</span>
        </div>
        <div className="flex justify-between text-xs">
          <span className="text-slate-400">{ru.checkout.recipient}</span>
          <span className="font-bold">@{recipientUsername || '...'}</span>
        </div>
        <div className="border-t border-slate-700/50 pt-2 flex justify-between text-base font-extrabold">
          <span>{ru.checkout.total}</span>
          <span className="text-blue-400">
            {product.estimated_price_rub ? `${(product.estimated_price_rub * (quantity / (product.default_quantity || 1))).toFixed(0)} ₽` : '...'}
          </span>
        </div>
        <p className="text-[11px] text-slate-400 text-center pt-2">
          ⏱️ {ru.checkout.orderTimeoutNotice}
        </p>
      </div>

      {error && (
        <div className="p-3 rounded-xl bg-red-500/20 border border-red-500/30 text-xs text-red-400 text-center">
          {error}
        </div>
      )}

      {/* Submit Button */}
      <button
        onClick={handleCreateOrder}
        disabled={submitting || (!!validationError)}
        className="w-full py-4 rounded-xl bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 disabled:opacity-50 text-white font-bold text-base shadow-lg shadow-blue-500/25 flex items-center justify-center space-x-2 transition-all active:scale-[0.98]"
      >
        {submitting ? (
          <>
            <Loader2 className="w-5 h-5 animate-spin" />
            <span>Создание счёта...</span>
          </>
        ) : (
          <span>{ru.common.pay}</span>
        )}
      </button>
    </div>
  );
};
