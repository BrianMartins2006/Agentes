import { useEffect, useState } from 'react';

export function useIrrigationNotifications(advice, device) {
  const supported = typeof window.Notification !== 'undefined';
  const [permission, setPermission] = useState(() => supported ? Notification.permission : 'unsupported');
  const [hint, setHint] = useState('');
  async function enable() {
    if (!supported) { setHint('Este navegador não oferece notificações nesta página.'); return; }
    try {
      const result = await Notification.requestPermission();
      setPermission(result);
      setHint(result === 'granted' ? 'Avisos ativados enquanto esta página estiver aberta.' :
        'Permita notificações nas configurações do site para receber os avisos.');
    } catch {
      setHint('Não foi possível ativar notificações. O aviso continua disponível no painel.');
    }
  }
  useEffect(() => {
    if (!supported || !device || permission !== 'granted' || !advice) return;
    const storageKey = `irrigation-notification:${device}`;
    if (!advice.notify) {
      if (advice.state === 'normal' || advice.state === 'inspect') {
        try { sessionStorage.removeItem(storageKey); } catch { /* Storage can be disabled. */ }
      }
      return;
    }
    const age = Date.now() - new Date(advice.based_on).getTime();
    if (!Number.isFinite(age) || age < -60000 || age > 300000) return;
    let last;
    try { last = JSON.parse(sessionStorage.getItem(storageKey) || 'null'); } catch { last = null; }
    if (last?.state === advice.state && Date.now() - last.at < 30 * 60000) return;
    try {
      const notification = new Notification(advice.title, {
        body: `${device}: ${advice.message}`,
        tag: `irrigation-${device}`,
      });
      notification.onclick = () => { window.focus(); notification.close(); };
      try { sessionStorage.setItem(storageKey, JSON.stringify({state: advice.state, at: Date.now()})); } catch { /* No credentials are stored. */ }
    } catch {
      setHint('Notificação não suportada neste dispositivo. Acompanhe o aviso no painel.');
    }
  }, [advice, device, permission, supported]);
  return {permission, enable, hint, supported};
}
