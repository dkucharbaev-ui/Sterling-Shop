import React, { useState, useEffect } from 'react';
import { RefreshCw, ExternalLink, AlertCircle, CheckCircle2, Clock, Loader2 } from 'lucide-react';
import { ru } from '../i18n/ru';
import { api } from '../api/client';
import { Order, OrderStatus } from '../types';

interface OrdersProps {
  onRepeatOrder: (productId: string, quantity: number) => void;
  haptic: (style: 'light' | 'medium' | 'heavy') => void;
  openLink: (url: string) => void;
  isDark: boolean;
}

export const Orders: React.FC<OrdersProps> = ({
  onRepeatOrder,
  haptic,
  openLink,
  isDark,
}) => {
  const [orders, setOrders] = useState<Order[]>([]);
  const [loading, setLoading] = useState<boolean>(true);

  const fetchOrders = async () => {
    try {
      const data = await api.getMyOrders();
      setOrders(data);
    } catch (e) {
      // Handle error
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchOrders();
    // Poll every 5 seconds for status updates
    const interval = setInterval(fetchOrders, 5000);
    return () => clearInterval(interval);
  }, []);

  const getStatusBadge = (status: OrderStatus) => {
    switch (status) {
      case 'COMPLETED':
        return (
          <span className="inline-flex items-center space-x-1 px-2.5 py-1 rounded-full text-xs font-bold bg-emerald-500/20 text-emerald-400 border border-emerald-500/30">
            <CheckCircle2 className="w-3.5 h-3.5" />
            <span>{ru.orders.status.COMPLETED}</span>
          </span>
        );
      case 'AWAITING_PAYMENT':
      case 'CREATED':
        return (
          <span className="inline-flex items-center space-x-1 px-2.5 py-1 rounded-full text-xs font-bold bg-amber-500/20 text-amber-400 border border-amber-500/30">
            <Clock className="w-3.5 h-3.5" />
            <span>{ru.orders.status.AWAITING_PAYMENT}</span>
          </span>
        );
      case 'PAID':
      case 'FULFILLING':
        return (
          <span className="inline-flex items-center space-x-1 px-2.5 py-1 rounded-full text-xs font-bold bg-blue-500/20 text-blue-400 border border-blue-500/30">
            <Loader2 className="w-3.5 h-3.5 animate-spin" />
            <span>{ru.orders.status.FULFILLING}</span>
          </span>
        );
      case 'REFUND_PENDING':
        return (
          <span className="inline-flex items-center space-x-1 px-2.5 py-1 rounded-full text-xs font-bold bg-purple-500/20 text-purple-400 border border-purple-500/30">
            <AlertCircle className="w-3.5 h-3.5" />
            <span>{ru.orders.status.REFUND_PENDING}</span>
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center space-x-1 px-2.5 py-1 rounded-full text-xs font-bold bg-slate-500/20 text-slate-400 border border-slate-500/30">
            <span>{ru.orders.status[status] || status}</span>
          </span>
        );
    }
  };

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-bold">{ru.orders.title}</h2>
        <button
          onClick={() => {
            haptic('light');
            fetchOrders();
          }}
          className={`p-2 rounded-xl text-slate-400 hover:text-white ${isDark ? 'bg-[#212d3b]' : 'bg-white shadow-sm'}`}
        >
          <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
        </button>
      </div>

      {orders.length === 0 && !loading && (
        <div className={`p-8 rounded-2xl text-center ${isDark ? 'bg-[#212d3b]' : 'bg-white shadow-sm'}`}>
          <p className="text-sm text-slate-400">{ru.orders.empty}</p>
        </div>
      )}

      <div className="space-y-3">
        {orders.map((o) => (
          <div
            key={o.id}
            className={`p-4 rounded-2xl border ${
              isDark ? 'bg-[#212d3b] border-slate-800' : 'bg-white border-slate-200 shadow-sm'
            } space-y-3`}
          >
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold text-slate-400">
                Заказ #{o.order_number}
              </span>
              {getStatusBadge(o.status)}
            </div>

            <div className="grid grid-cols-2 gap-2 text-xs">
              <div>
                <span className="text-slate-400 block">Получатель:</span>
                <span className="font-semibold text-slate-200">@{o.recipient_username}</span>
              </div>
              <div>
                <span className="text-slate-400 block">Количество:</span>
                <span className="font-semibold text-slate-200">{o.quantity} шт.</span>
              </div>
              <div>
                <span className="text-slate-400 block">Сумма:</span>
                <span className="font-bold text-blue-400">{o.fiat_amount} {o.fiat_currency}</span>
              </div>
              <div>
                <span className="text-slate-400 block">Оплата через:</span>
                <span className="font-semibold text-slate-200">{o.payment_provider}</span>
              </div>
            </div>

            {/* Actions */}
            <div className="pt-2 border-t border-slate-700/40 flex items-center justify-between">
              {(o.status === 'CREATED' || o.status === 'AWAITING_PAYMENT') && o.payment_url && (
                <button
                  onClick={() => {
                    haptic('medium');
                    openLink(o.payment_url!);
                  }}
                  className="px-4 py-2 rounded-xl bg-blue-600 hover:bg-blue-500 text-white font-bold text-xs flex items-center space-x-1 shadow-md shadow-blue-500/20"
                >
                  <span>Оплатить счёт</span>
                  <ExternalLink className="w-3.5 h-3.5" />
                </button>
              )}

              {o.status === 'COMPLETED' && (
                <button
                  onClick={() => {
                    haptic('light');
                    onRepeatOrder(o.product_id, o.quantity);
                  }}
                  className="px-3 py-1.5 rounded-xl bg-slate-700 hover:bg-slate-600 text-white font-semibold text-xs"
                >
                  {ru.orders.repeatOrder}
                </button>
              )}

              <a
                href={`https://t.me/PsychoSupport?text=Вопрос по заказу %23${o.order_number}`}
                target="_blank"
                rel="noreferrer"
                className="text-xs text-blue-400 hover:underline ml-auto"
              >
                {ru.orders.contactSupport}
              </a>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
