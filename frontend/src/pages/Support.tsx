import React, { useState } from 'react';
import { MessageCircle, HelpCircle, ChevronDown, ChevronUp, ShieldCheck, Zap } from 'lucide-react';
import { ru } from '../i18n/ru';

interface SupportProps {
  isDark: boolean;
  haptic: (style: 'light' | 'medium' | 'heavy') => void;
}

const FAQS = [
  {
    q: 'Как быстро начисляются Telegram Stars и Premium?',
    a: 'Выдача происходит автоматически через защищенный смарт-контракт сразу после подтверждения оплаты. Обычно это занимает от 30 секунд до 2 минут.',
  },
  {
    q: 'Нужен ли пароль от Telegram аккаунта?',
    a: 'Нет! Никогда и никому не сообщайте пароли. Выдача производится исключительно по вашему публичному @username.',
  },
  {
    q: 'Можно ли купить Stars или Premium в подарок другу?',
    a: 'Да! При оформлении заказа выберите пункт «В подарок» и введите @username получателя.',
  },
  {
    q: 'Что делать, если заказ не пришёл или возникла ошибка?',
    a: 'Система автоматически фиксирует любые сбои. Если выдача не удалась, заказ переходит в статус ожидания возврата, а наша поддержка мгновенно поможет вам.',
  },
];

export const Support: React.FC<SupportProps> = ({ isDark, haptic }) => {
  const [openIdx, setOpenIdx] = useState<number | null>(null);

  const toggle = (idx: number) => {
    haptic('light');
    setOpenIdx(openIdx === idx ? null : idx);
  };

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-xl font-bold flex items-center space-x-2">
          <HelpCircle className="w-5 h-5 text-blue-400" />
          <span>{ru.home.faq}</span>
        </h2>
        <p className="text-xs text-slate-400 mt-1">Ответы на популярные вопросы о покупке и доставке</p>
      </div>

      <div className="space-y-2.5">
        {FAQS.map((faq, idx) => {
          const isOpen = openIdx === idx;
          return (
            <div
              key={idx}
              className={`rounded-2xl border transition-all overflow-hidden ${
                isDark ? 'bg-[#212d3b] border-slate-800' : 'bg-white border-slate-200 shadow-sm'
              }`}
            >
              <button
                onClick={() => toggle(idx)}
                className="w-full p-4 text-left flex items-center justify-between text-sm font-semibold"
              >
                <span>{faq.q}</span>
                {isOpen ? <ChevronUp className="w-4 h-4 text-slate-400 shrink-0" /> : <ChevronDown className="w-4 h-4 text-slate-400 shrink-0" />}
              </button>
              {isOpen && (
                <div className="px-4 pb-4 text-xs text-slate-400 leading-relaxed border-t border-slate-700/30 pt-3">
                  {faq.a}
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* Operator button */}
      <div className={`p-6 rounded-2xl text-center ${isDark ? 'bg-[#212d3b]' : 'bg-white shadow-sm'} space-y-3`}>
        <div className="w-12 h-12 rounded-full bg-blue-500/20 text-blue-400 mx-auto flex items-center justify-center">
          <MessageCircle className="w-6 h-6" />
        </div>
        <h3 className="font-bold text-base">Остались вопросы?</h3>
        <p className="text-xs text-slate-400 max-w-xs mx-auto">
          Наша служба заботы на связи 24/7 и с радостью ответит на любые вопросы
        </p>
        <a
          href="https://t.me/PsychoSupport"
          target="_blank"
          rel="noreferrer"
          className="inline-flex items-center space-x-2 px-6 py-3 rounded-xl bg-blue-600 hover:bg-blue-500 text-white font-bold text-xs shadow-md shadow-blue-500/25 transition-all"
        >
          <MessageCircle className="w-4 h-4" />
          <span>Связаться с оператором</span>
        </a>
      </div>
    </div>
  );
};
