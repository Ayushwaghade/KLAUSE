import React, { useState, useEffect, useRef, useCallback } from 'react';
import { useStore } from '../store/useStore';
import { useWebSocket } from '../hooks/useWebSocket';
import { useVoiceAmplitude } from '../hooks/useVoiceAmplitude';
import { useOrbState } from '../hooks/useOrbState';
import { Mic, Send, ChevronDown, ChevronRight, Square } from 'lucide-react';
import type { ChatMessage } from '../types/api';

/* ─── Tool Card (expandable) ─── */
const ToolCard: React.FC<{ msg: ChatMessage; observation?: ChatMessage }> = ({ msg, observation }) => {
  const [expanded, setExpanded] = useState(false);
  const hasObs = !!observation;
  const success = observation?.observation?.success ?? true;

  return (
    <div className="chat-tool-card">
      <div className="chat-tool-card__header" onClick={() => setExpanded(v => !v)}>
        <span className="chat-tool-card__name">
          {hasObs && (
            <span className={`chat-tool-card__status ${
              success ? 'chat-tool-card__status--success' : 'chat-tool-card__status--error'
            }`} />
          )}
          {msg.action || 'tool_call'}
        </span>
        <span className="chat-tool-card__toggle">
          {expanded ? <ChevronDown size={10} /> : <ChevronRight size={10} />}
        </span>
      </div>
      {expanded && (
        <div className="chat-tool-card__body">
          {msg.params && Object.keys(msg.params).length > 0 && (
            <pre className="chat-tool-card__params">{JSON.stringify(msg.params, null, 2)}</pre>
          )}
          {observation && (
            <pre className={`chat-tool-card__result ${
              success ? 'chat-tool-card__result--success' : 'chat-tool-card__result--error'
            }`}>
              {success ? (observation.observation?.result || 'Done.') : (observation.observation?.error || 'Error.')}
            </pre>
          )}
        </div>
      )}
    </div>
  );
};

/* ─── Main Chat Page ─── */
export const ChatPage: React.FC = () => {
  const [inputText, setInputText] = useState('');
  const messagesEndRef = useRef<HTMLDivElement | null>(null);

  const messages = useStore(state => state.messages);
  const voiceActive = useStore(state => state.voiceInputActive);
  const setVoiceActive = useStore(state => state.setVoiceInputActive);
  const token = useStore(state => state.token);
  const connectionStatus = useStore(state => state.connectionStatus);
  const orbState = useStore(state => state.orbState);

  const { sendMessage, interruptActiveSession, sendConfirmationResponse } = useWebSocket();
  const { startListening, stopListening } = useVoiceAmplitude();
  const { transition } = useOrbState();

  const handleSend = useCallback(() => {
    if (!inputText.trim()) return;
    sendMessage(inputText.trim());
    setInputText('');
  }, [inputText, sendMessage]);

  const handleKeyPress = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') handleSend();
  };

  const toggleVoice = async () => {
    const isCurrentlyActive = useStore.getState().voiceInputActive;

    if (isCurrentlyActive) {
      const wavBlob = stopListening();
      setVoiceActive(false);
      transition('START_PROCESSING');

      if (wavBlob) {
        const audioWs = new WebSocket(`ws://127.0.0.1:8000/ws/audio?token=${token}`);
        audioWs.onopen = () => {
          const reader = new FileReader();
          reader.onload = () => {
            if (reader.result instanceof ArrayBuffer) audioWs.send(reader.result);
          };
          reader.readAsArrayBuffer(wavBlob);
        };
        audioWs.onmessage = (event) => {
          try {
            const res = JSON.parse(event.data);
            if (res.type === 'transcript' && res.text.trim()) {
              sendMessage(res.text);
            } else {
              transition('FINISH');
            }
          } catch {
            transition('FINISH');
          }
          audioWs.close();
        };
        audioWs.onerror = () => transition('ERROR');
      } else {
        transition('FINISH');
      }
    } else {
      setVoiceActive(true);
      transition('START_LISTENING');
      await startListening();
      setTimeout(() => {
        if (useStore.getState().voiceInputActive) toggleVoice();
      }, 8000);
    }
  };

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  /* ─── Group messages into reasoning chains ─── */
  const renderMessages = () => {
    const elements: React.ReactNode[] = [];
    let i = 0;

    while (i < messages.length) {
      const msg = messages[i];

      // User prompt bubble
      if (msg.sender === 'user') {
        elements.push(
          <div key={msg.id} className="chat-msg chat-msg--user">
            <div className="chat-bubble chat-bubble--user">
              <div className="chat-bubble__text">{msg.text}</div>
              <span className="chat-bubble__time">{msg.timestamp}</span>
            </div>
          </div>
        );
        i++;
        continue;
      }

      // Confirmation request message
      if (msg.type === 'confirmation_request') {
        elements.push(
          <div key={msg.id} className="chat-msg chat-msg--agent animate-slide-in">
            <div className="chat-confirmation-card">
              <div className="chat-confirmation-card__header">
                <span className="chat-confirmation-card__title">Permission Required</span>
              </div>
              <div className="chat-confirmation-card__body">
                <p className="chat-confirmation-card__text">{msg.text}</p>
                {msg.confirmation_status === 'pending' ? (
                  <div className="chat-confirmation-card__actions">
                    <button
                      className="chat-confirmation-btn chat-confirmation-btn--approve"
                      onClick={() => sendConfirmationResponse(msg.id, msg.request_id || '', true)}
                    >
                      Approve (Yes)
                    </button>
                    <button
                      className="chat-confirmation-btn chat-confirmation-btn--deny"
                      onClick={() => sendConfirmationResponse(msg.id, msg.request_id || '', false)}
                    >
                      Deny (No)
                    </button>
                  </div>
                ) : (
                  <div className={`chat-confirmation-status chat-confirmation-status--${msg.confirmation_status}`}>
                    {msg.confirmation_status === 'approved' ? '✓ Approved' : '✗ Denied'}
                  </div>
                )}
              </div>
            </div>
          </div>
        );
        i++;
        continue;
      }

      // Collect a reasoning chain: consecutive thought/observation messages
      const chainStart = i;
      const chain: ChatMessage[] = [];
      while (i < messages.length && (messages[i].type === 'thought' || messages[i].type === 'observation')) {
        chain.push(messages[i]);
        i++;
      }

      // If we collected a chain, render it inside a timeline container
      if (chain.length > 0) {
        elements.push(
          <div key={`chain-${chainStart}`} className="chat-timeline">
            {chain.map((step, idx) => {
              if (step.type === 'thought') {
                // Find the matching observation (next message if it's an observation with same step)
                const nextMsg = chain[idx + 1];
                const matchingObs = nextMsg?.type === 'observation' && nextMsg.step === step.step ? nextMsg : undefined;

                return (
                  <React.Fragment key={step.id}>
                    {/* Thought monologue */}
                    <div className="chat-thought">
                      <span className="chat-thought__dot" />
                      <div className="chat-thought__content">
                        <span className="chat-thought__step">STEP {step.step}</span>
                        {step.thought && (
                          <span className="chat-thought__text">{step.thought}</span>
                        )}
                      </div>
                    </div>
                    {/* Tool card (thought + observation fused) */}
                    {step.action && (
                      <ToolCard msg={step} observation={matchingObs} />
                    )}
                  </React.Fragment>
                );
              }
              // Skip observations that were already consumed by the thought above
              if (step.type === 'observation') {
                const prevMsg = chain[idx - 1];
                if (prevMsg?.type === 'thought' && prevMsg.step === step.step) return null;
                // Orphan observation — render standalone
                return (
                  <div key={step.id} className="chat-tool-card">
                    <div className="chat-tool-card__header">
                      <span className="chat-tool-card__name">
                        <span className={`chat-tool-card__status ${
                          step.observation?.success ? 'chat-tool-card__status--success' : 'chat-tool-card__status--error'
                        }`} />
                        Result — Step {step.step}
                      </span>
                    </div>
                    <div className="chat-tool-card__body">
                      <pre className={`chat-tool-card__result ${
                        step.observation?.success ? 'chat-tool-card__result--success' : 'chat-tool-card__result--error'
                      }`}>
                        {step.observation?.success ? (step.observation.result || 'Done.') : (step.observation?.error || 'Error.')}
                      </pre>
                    </div>
                  </div>
                );
              }
              return null;
            })}
          </div>
        );
      }

      // Final response bubble (agent's spoken answer)
      if (i < messages.length && messages[i].type === 'final') {
        const final = messages[i];
        elements.push(
          <div key={final.id} className="chat-final">
            <div className="chat-final__bubble">
              <div className="chat-final__text">
                {final.text}
                {final.streaming && <span className="chat-cursor" />}
              </div>
              {!final.streaming && (
                <div className="chat-final__time">{final.timestamp}</div>
              )}
            </div>
          </div>
        );
        i++;
        continue;
      }

      // Fallback: any other agent message (prompt type, etc.)
      if (i < messages.length) {
        const fallback = messages[i];
        elements.push(
          <div key={fallback.id} className="chat-msg chat-msg--agent">
            <div className="chat-bubble chat-bubble--agent">
              <div className="chat-bubble__text">{fallback.text || fallback.thought}</div>
              <span className="chat-bubble__time">{fallback.timestamp}</span>
            </div>
          </div>
        );
        i++;
      }
    }

    return elements;
  };

  const isAgentActive = orbState === 'processing' || orbState === 'responding';

  return (
    <div className="chat-page">
      {/* Connection status bar */}
      <div className="chat-toolbar">
        <div className="chat-toolbar__status">
          <span className={`chat-toolbar__dot ${connectionStatus === 'connected' ? 'chat-toolbar__dot--on' : ''}`} />
          <span className="chat-toolbar__label">{connectionStatus.toUpperCase()}</span>
        </div>
      </div>

      {/* Chat feed */}
      <div className="chat-feed fade-scroll-container">
        {messages.length === 0 ? (
          <div className="chat-welcome">
            <h2 className="chat-welcome__title">Hello, Ayush.</h2>
            <p className="chat-welcome__sub">Speak or type your request below.</p>
          </div>
        ) : (
          renderMessages()
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Input area */}
      <div className="chat-input-area">
        <button
          className={`chat-mic ${voiceActive ? 'chat-mic--active' : ''}`}
          onClick={toggleVoice}
          title={voiceActive ? 'Stop Recording' : 'Voice Command'}
        >
          <Mic size={18} color={voiceActive ? '#fff' : 'var(--accent-cyan)'} />
        </button>
        <input
          type="text"
          className="chat-input"
          placeholder={isAgentActive ? "Agent executing... type to auto-interrupt" : "Ask KLAUSE..."}
          value={inputText}
          onChange={(e) => setInputText(e.target.value)}
          onKeyDown={handleKeyPress}
        />
        {isAgentActive && (
          <button
            className="chat-stop"
            onClick={() => interruptActiveSession()}
            title="Interrupt Agent"
          >
            <Square size={14} color="#f44336" fill="#f44336" />
          </button>
        )}
        <button className="chat-send" onClick={handleSend} disabled={!inputText.trim()}>
          <Send size={15} color="#fff" />
        </button>
      </div>
    </div>
  );
};
