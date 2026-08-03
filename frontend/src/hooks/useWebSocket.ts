import { useEffect, useRef, useCallback } from 'react';
import { useStore } from '../store/useStore';
import { useOrbState } from './useOrbState';

const WS_URL = 'ws://127.0.0.1:8000/ws/chat';

export function useWebSocket() {
  const socketRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<number | null>(null);
  const reconnectDelayRef = useRef<number>(1000); // Start with 1s
  const hasReceivedFirstTokenRef = useRef<boolean>(false);

  const token = useStore(state => state.token);
  const connectionStatus = useStore(state => state.connectionStatus);
  const setConnectionStatus = useStore(state => state.setConnectionStatus);
  const addMessage = useStore(state => state.addMessage);
  const updateMessage = useStore(state => state.updateMessage);
  const appendToLastMessage = useStore(state => state.appendToLastMessage);
  const addToast = useStore(state => state.addToast);

  const { transition } = useOrbState();

  const connect = useCallback(() => {
    if (!token) return;

    if (socketRef.current) {
      socketRef.current.close();
    }

    setConnectionStatus('connecting');
    const ws = new WebSocket(`${WS_URL}?token=${token}`);
    socketRef.current = ws;

    ws.onopen = () => {
      setConnectionStatus('connected');
      transition('FINISH');
      reconnectDelayRef.current = 1000; // Reset reconnect delay
      console.log("WS Chat: Connected successfully.");
      addToast("Secure link established", "success");
    };

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        console.log("WS Chat: Received message:", data);

        if (data.type === 'thought') {
          transition('START_PROCESSING');
          hasReceivedFirstTokenRef.current = false;
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
        } else if (data.type === 'request_confirmation') {
          addMessage({
            sender: 'system',
            type: 'confirmation_request',
            request_id: data.request_id,
            text: data.prompt,
            confirmation_status: 'pending'
          });
          addToast("Permission requested", "warning");
        } else if (data.type === 'token') {
          // Response streaming token
          if (!hasReceivedFirstTokenRef.current) {
            hasReceivedFirstTokenRef.current = true;
            transition('START_RESPONDING');
            // Create initial final message with streaming cursor
            addMessage({
              sender: 'klause',
              type: 'final',
              text: data.text || '',
              streaming: true
            });
          } else {
            // Append incoming text segment
            appendToLastMessage(data.text || '');
          }
        } else if (data.type === 'final') {
          transition('FINISH');
          
          const msgs = useStore.getState().messages;
          const lastMsg = msgs[msgs.length - 1];

          // If we had a streaming response, close it
          if (lastMsg && lastMsg.type === 'final' && lastMsg.streaming) {
            // Simply mark the last message as done (it already has all the text)
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
            // Fallback: append complete response if no streaming tokens were sent
            addMessage({
              sender: 'klause',
              type: 'final',
              text: data.response,
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
  }, [token, setConnectionStatus, addMessage, appendToLastMessage, addToast, transition]);

  const triggerReconnect = () => {
    if (reconnectTimeoutRef.current) return;
    
    const delay = reconnectDelayRef.current;
    console.log(`WS Chat: Attempting reconnect in ${delay}ms`);
    
    reconnectTimeoutRef.current = window.setTimeout(() => {
      reconnectTimeoutRef.current = null;
      // Exponential backoff with 30s cap
      reconnectDelayRef.current = Math.min(30000, reconnectDelayRef.current * 2);
      connect();
    }, delay);
  };

  const sendMessage = useCallback((prompt: string, sessionId: string = 'default_session') => {
    if (socketRef.current && socketRef.current.readyState === WebSocket.OPEN) {
      transition('START_PROCESSING');
      hasReceivedFirstTokenRef.current = false;
      
      // Add user message to local state
      addMessage({
        sender: 'user',
        type: 'prompt',
        text: prompt
      });

      socketRef.current.send(JSON.stringify({
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
    if (socketRef.current && socketRef.current.readyState === WebSocket.OPEN) {
      socketRef.current.send(JSON.stringify({
        type: 'interrupt',
        session_id: sessionId
      }));
      transition('FINISH');
      useStore.getState().setVoiceInputActive(false);
      addToast("Agent execution interrupted", "info");
    }
  }, [transition, addToast]);

  const sendConfirmationResponse = useCallback((messageId: string, requestId: string, approved: boolean, sessionId: string = 'default_session') => {
    if (socketRef.current && socketRef.current.readyState === WebSocket.OPEN) {
      socketRef.current.send(JSON.stringify({
        type: 'confirmation_response',
        session_id: sessionId,
        request_id: requestId,
        approved: approved
      }));
      updateMessage(messageId, { confirmation_status: approved ? 'approved' : 'denied' });
      addToast(approved ? "Permission approved" : "Permission denied", approved ? "success" : "info");
    }
  }, [updateMessage, addToast]);

  useEffect(() => {
    if (token) {
      connect();
    }

    return () => {
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
      if (socketRef.current) {
        socketRef.current.onclose = null; // Prevent reconnect loop on clean unmount
        socketRef.current.close();
      }
    };
  }, [token, connect]);

  return {
    connectionStatus,
    sendMessage,
    interruptActiveSession,
    sendConfirmationResponse
  };
}
