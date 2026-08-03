import React, { useEffect } from 'react';
import { useStore } from '../store/useStore';

const borderColors: Record<string, string> = {
  info: 'rgba(79, 195, 247, 0.6)',    // cyan
  success: 'rgba(76, 175, 80, 0.6)',   // green
  warning: 'rgba(255, 179, 0, 0.6)',   // amber
};

const containerStyle: React.CSSProperties = {
  position: 'fixed',
  left: 24,
  bottom: 72,
  zIndex: 90,
  display: 'flex',
  flexDirection: 'column',
  gap: 6,
  pointerEvents: 'none',
};

const toastStyle: React.CSSProperties = {
  background: 'rgba(11, 13, 19, 0.85)',
  border: '1px solid rgba(79, 195, 247, 0.2)',
  borderRadius: 8,
  padding: '8px 14px',
  fontSize: 12,
  fontFamily: "'JetBrains Mono', monospace",
  color: 'rgba(232, 249, 255, 0.7)',
  backdropFilter: 'blur(12px)',
  pointerEvents: 'auto',
  animation: 'toastSlideIn 250ms ease-out forwards',
};

// Inject keyframes once
const styleId = '__toast-feed-keyframes__';
if (typeof document !== 'undefined' && !document.getElementById(styleId)) {
  const style = document.createElement('style');
  style.id = styleId;
  style.textContent = `
    @keyframes toastSlideIn {
      from {
        opacity: 0;
        transform: translateY(8px);
      }
      to {
        opacity: 1;
        transform: translateY(0);
      }
    }
  `;
  document.head.appendChild(style);
}

interface ToastItemProps {
  id: string;
  message: string;
  type: 'info' | 'success' | 'warning';
}

const ToastItem: React.FC<ToastItemProps> = ({ id, message, type }) => {
  const removeToast = useStore(state => state.removeToast);

  useEffect(() => {
    const timer = setTimeout(() => {
      removeToast(id);
    }, 3000);
    return () => clearTimeout(timer);
  }, [id, removeToast]);

  return (
    <div
      style={{
        ...toastStyle,
        borderLeft: `3px solid ${borderColors[type] || borderColors.info}`,
      }}
    >
      {message}
    </div>
  );
};

export const ToastFeed: React.FC = () => {
  const toasts = useStore(state => state.toasts);

  if (toasts.length === 0) return null;

  return (
    <div style={containerStyle}>
      {toasts.map(toast => (
        <ToastItem
          key={toast.id}
          id={toast.id}
          message={toast.message}
          type={toast.type}
        />
      ))}
    </div>
  );
};

export default ToastFeed;
