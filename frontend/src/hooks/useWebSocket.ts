import { useEffect, useCallback } from 'react';
import { useStore } from '../store/useStore';
import { useOrbState } from './useOrbState';

const WS_URL = 'ws://127.0.0.1:8000/ws/chat';

// Module-level shared singleton socket across all hook consumers
let sharedWs: WebSocket | null = null;
let reconnectTimeout: number | null = null;
let reconnectDelay = 1000; // Start with 1s
let hasReceivedFirstToken = false;

export function useWebSocket() {
  const token = useStore(state => state.token);
  const connectionStatus = useStore(state => state.connectionStatus);
  const setConnectionStatus = useStore(state => state.setConnectionStatus);
  const addMessage = useStore(state => state.addMessage);
  const updateMessage = useStore(state => state.updateMessage);
  const appendToLastMessage = useStore(state => state.appendToLastMessage);
  const addToast = useStore(state => state.addToast);
  const setPendingConfirmation = useStore(state => state.setPendingConfirmation);

  const { transition } = useOrbState();

  const connect = useCallback(() => {
    if (!token) return;

    // Reuse existing connection if already connecting or open
    if (sharedWs && (sharedWs.readyState === WebSocket.OPEN || sharedWs.readyState === WebSocket.CONNECTING)) {
      return;
    }

    if (sharedWs) {
      try {
        sharedWs.close();
      } catch {
        // ignore
      }
    }

    setConnectionStatus('connecting');
    const ws = new WebSocket(`${WS_URL}?token=${token}`);
    sharedWs = ws;

    ws.onopen = () => {
      setConnectionStatus('connected');
      transition('FINISH');
      reconnectDelay = 1000; // Reset reconnect delay
      console.log("WS Chat: Connected successfully.");
      addToast("Secure link established", "success");
    };

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        console.log("WS Chat: Received message:", data);

        if (data.type === 'thought') {
          transition('START_PROCESSING');
          hasReceivedFirstToken = false;
          // When a thought arrives, any waiting confirmation was answered or bypassed
          setPendingConfirmation(null);
          addMessage({
            sender: 'klause',
            type: 'thought',
            step: data.step,
            thought: data.thought,
            action: data.action,
            params: data.params
          });
          if (data.action) {
            addToast(`Tool invocation: ${data.action}`, "info");
          }
        } else if (data.type === 'observation') {
          addMessage({
            sender: 'system',
            type: 'observation',
            step: data.step,
            observation: data.observation
          });
          if (data.observation?.success) {
            addToast(`Step ${data.step} completed successfully`, "success");
          } else {
            addToast(`Step ${data.step} reported errors`, "warning");
          }
        } else if (data.type === 'user_prompt' || data.type === 'prompt') {
          addMessage({
            sender: 'user',
            type: 'prompt',
            text: data.text || data.prompt || ''
          });
        } else if (data.type === 'request_confirmation') {
          const msgId = Math.random().toString(36).substring(7);
          addMessage({
            sender: 'system',
            type: 'confirmation_request',
            request_id: data.request_id,
            text: data.prompt,
            confirmation_status: 'pending'
          });
          // Update global pending confirmation for floating popup card on HUD
          setPendingConfirmation({
            id: msgId,
            requestId: data.request_id,
            prompt: data.prompt,
            sessionId: data.session_id || 'default_session'
          });
          addToast("Permission requested", "warning");
        } else if (data.type === 'token') {
          // Response streaming token
          if (!hasReceivedFirstToken) {
            hasReceivedFirstToken = true;
            transition('START_RESPONDING');
            addMessage({
              sender: 'klause',
              type: 'final',
              text: data.text || '',
              streaming: true
            });
          } else {
            appendToLastMessage(data.text || '');
          }
        } else if (data.type === 'final') {
          transition('FINISH');
          setPendingConfirmation(null);

          const msgs = useStore.getState().messages;
          const lastMsg = msgs[msgs.length - 1];

          // If we had a streaming response, close it
          if (lastMsg && lastMsg.type === 'final' && lastMsg.streaming) {
            useStore.setState(state => {
              const newMsgs = [...state.messages];
              if (newMsgs.length > 0) {
                newMsgs[newMsgs.length - 1] = {
                  ...newMsgs[newMsgs.length - 1],
                  streaming: false,
                  timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
                };
              }
              return { messages: newMsgs };
            });
          } else {
            addMessage({
              sender: 'klause',
              type: 'final',
              text: data.response || data.text || '',
              streaming: false
            });
          }
          addToast("Response fully generated", "success");
        }
      } catch (err) {
        console.error("WS Chat: Failed to parse WS message payload:", err);
      }
    };

    ws.onclose = () => {
      setConnectionStatus('disconnected');
      transition('FINISH');
      console.log("WS Chat: Connection closed. Retrying...");
      triggerReconnect();
    };

    ws.onerror = (err) => {
      console.error("WS Chat: Socket error:", err);
      transition('ERROR');
      addToast("Secure link failure", "warning");
      ws.close();
    };
  }, [token, setConnectionStatus, addMessage, appendToLastMessage, addToast, setPendingConfirmation, transition]);

  const triggerReconnect = () => {
    if (reconnectTimeout) return;

    const delay = reconnectDelay;
    console.log(`WS Chat: Attempting reconnect in ${delay}ms`);

    reconnectTimeout = window.setTimeout(() => {
      reconnectTimeout = null;
      reconnectDelay = Math.min(30000, reconnectDelay * 2);
      connect();
    }, delay);
  };

  const sendMessage = useCallback((prompt: string, sessionId: string = 'default_session') => {
    if (sharedWs && sharedWs.readyState === WebSocket.OPEN) {
      transition('START_PROCESSING');
      hasReceivedFirstToken = false;

      // Add user message to local state
      addMessage({
        sender: 'user',
        type: 'prompt',
        text: prompt
      });

      sharedWs.send(JSON.stringify({
        session_id: sessionId,
        prompt: prompt
      }));
    } else {
      console.warn("WS Chat: Cannot send message. Socket is not open.");
      transition('ERROR');
      addToast("Secure link offline", "warning");
    }
  }, [addMessage, transition, addToast]);

  const interruptActiveSession = useCallback((sessionId: string = 'default_session') => {
    if (sharedWs && sharedWs.readyState === WebSocket.OPEN) {
      sharedWs.send(JSON.stringify({
        type: 'interrupt',
        session_id: sessionId
      }));
      transition('FINISH');
      useStore.getState().setVoiceInputActive(false);
      useStore.getState().setPendingConfirmation(null);
      addToast("Agent execution interrupted", "info");
    }
  }, [transition, addToast]);

  const sendConfirmationResponse = useCallback((messageId: string, requestId: string, approved: boolean, sessionId: string = 'default_session') => {
    if (sharedWs && sharedWs.readyState === WebSocket.OPEN) {
      sharedWs.send(JSON.stringify({
        type: 'confirmation_response',
        session_id: sessionId,
        request_id: requestId,
        approved: approved
      }));
      updateMessage(messageId, { confirmation_status: approved ? 'approved' : 'denied' });
      setPendingConfirmation(null);
      addToast(approved ? "Permission approved" : "Permission denied", approved ? "success" : "info");
    }
  }, [updateMessage, addToast, setPendingConfirmation]);

  useEffect(() => {
    if (token) {
      connect();
    }
  }, [token, connect]);

  return {
    connectionStatus,
    sendMessage,
    interruptActiveSession,
    sendConfirmationResponse
  };
}

export default useWebSocket;
