import React, { useEffect, useCallback } from 'react';
import { useWebSocket } from '../hooks/useWebSocket';
import { ShieldAlert, Check, X, Terminal } from 'lucide-react';
import type { PendingConfirmation } from '../store/useStore';

interface ConfirmationPopupProps {
  pending: PendingConfirmation;
}

export const ConfirmationPopup: React.FC<ConfirmationPopupProps> = ({ pending }) => {
  const { sendConfirmationResponse } = useWebSocket();

  const handleApprove = useCallback(() => {
    sendConfirmationResponse(pending.id, pending.requestId, true, pending.sessionId);
  }, [sendConfirmationResponse, pending]);

  const handleDeny = useCallback(() => {
    sendConfirmationResponse(pending.id, pending.requestId, false, pending.sessionId);
  }, [sendConfirmationResponse, pending]);

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      const tag = (e.target as HTMLElement)?.tagName?.toLowerCase();
      if (tag === 'input' || tag === 'textarea') return;

      if (e.key === 'y' || e.key === 'Y' || e.key === 'Enter') {
        e.preventDefault();
        handleApprove();
      } else if (e.key === 'n' || e.key === 'N' || e.key === 'Escape') {
        e.preventDefault();
        handleDeny();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [handleApprove, handleDeny]);

  return (
    <div className="hud-confirmation-card">
      <div className="hud-confirmation-card__header">
        <div className="hud-confirmation-card__badge">
          <ShieldAlert size={14} color="#ffb300" />
          <span>PERMISSION REQUIRED</span>
        </div>
      </div>
      <div className="hud-confirmation-card__content">
        <div className="hud-confirmation-card__prompt">
          <Terminal size={12} color="rgba(255, 179, 0, 0.8)" className="hud-confirmation-card__terminal-icon" />
          <span>{pending.prompt}</span>
        </div>
      </div>
      <div className="hud-confirmation-card__actions">
        <button
          className="hud-confirmation-btn hud-confirmation-btn--approve"
          onClick={handleApprove}
          title="Approve (Press Y or Enter)"
        >
          <Check size={13} />
          <span>Approve (Yes)</span>
        </button>
        <button
          className="hud-confirmation-btn hud-confirmation-btn--deny"
          onClick={handleDeny}
          title="Deny (Press N or Esc)"
        >
          <X size={13} />
          <span>Deny (No)</span>
        </button>
      </div>
      <div className="hud-confirmation-card__hint">
        [ Y / Enter ] Approve &nbsp;&bull;&nbsp; [ N / Esc ] Deny
      </div>
    </div>
  );
};

export default ConfirmationPopup;
