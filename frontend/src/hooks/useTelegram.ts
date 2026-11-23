import { useEffect, useState, useCallback } from 'react';

export function useTelegram() {
  const [tg, setTg] = useState<any>(null);
  const [user, setUser] = useState<any>(null);
  const [initData, setInitData] = useState<string>('');
  const [isDark, setIsDark] = useState<boolean>(true);

  useEffect(() => {
    const webapp = (window as any).Telegram?.WebApp;
    if (webapp) {
      webapp.ready();
      webapp.expand();
      setTg(webapp);
      setInitData(webapp.initData || '');
      setUser(webapp.initDataUnsafe?.user || null);
      setIsDark(webapp.colorScheme === 'dark');

      const handleTheme = () => {
        setIsDark(webapp.colorScheme === 'dark');
      };
      webapp.onEvent('themeChanged', handleTheme);
      return () => {
        webapp.offEvent('themeChanged', handleTheme);
      };
    }
  }, []);

  const haptic = useCallback(
    (style: 'light' | 'medium' | 'heavy' = 'light') => {
      try {
        tg?.HapticFeedback?.impactOccurred(style);
      } catch (e) {
        // Ignore if unsupported
      }
    },
    [tg]
  );

  const hapticNotification = useCallback(
    (type: 'error' | 'success' | 'warning' = 'success') => {
      try {
        tg?.HapticFeedback?.notificationOccurred(type);
      } catch (e) {
        // Ignore
      }
    },
    [tg]
  );

  const openLink = useCallback(
    (url: string) => {
      if (tg?.openTelegramLink && url.includes('t.me/')) {
        tg.openTelegramLink(url);
      } else if (tg?.openLink) {
        tg.openLink(url);
      } else {
        window.open(url, '_blank');
      }
    },
    [tg]
  );

  return {
    tg,
    user,
    initData,
    isDark,
    haptic,
    hapticNotification,
    openLink,
  };
}
