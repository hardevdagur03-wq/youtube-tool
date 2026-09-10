import { useCallback, useEffect, useState } from 'react';

interface Toast {
  id: string;
  type: 'success' | 'error' | 'info' | 'warning';
  message: string;
}

let addToastFn: ((toast: Omit<Toast, 'id'>) => void) | null = null;

export function showToast(type: Toast['type'], message: string) {
  addToastFn?.({ type, message });
}

export default function ToastContainer() {
  const [toasts, setToasts] = useState<Toast[]>([]);

  const addToast = useCallback((toast: Omit<Toast, 'id'>) => {
    const id = Date.now().toString(36) + Math.random().toString(36).slice(2, 5);
    setToasts((prev) => [...prev, { ...toast, id }]);
    setTimeout(() => {
      setToasts((prev) => prev.filter((t) => t.id !== id));
    }, 4000);
  }, []);

  useEffect(() => {
    addToastFn = addToast;
    return () => { addToastFn = null; };
  }, [addToast]);

  const dismiss = (id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  };

  if (toasts.length === 0) return null;

  return (
    <div className="fixed bottom-4 right-4 z-50 flex flex-col gap-2 max-w-sm">
      {toasts.map((toast) => (
        <div
          key={toast.id}
          className={`flex items-start gap-3 px-4 py-3 rounded-lg shadow-lg text-sm transition-all animate-slide-up ${
            toast.type === 'success' ? 'bg-green-600 text-white' :
            toast.type === 'error' ? 'bg-red-600 text-white' :
            toast.type === 'warning' ? 'bg-yellow-500 text-white' :
            'bg-blue-600 text-white'
          }`}
        >
          <span className="flex-1">{toast.message}</span>
          <button
            onClick={() => dismiss(toast.id)}
            className="text-white/80 hover:text-white ml-2"
          >
            x
          </button>
        </div>
      ))}
    </div>
  );
}
