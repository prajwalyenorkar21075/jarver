export type SocketConnectionState = 'connecting' | 'connected' | 'disconnected' | 'error';

type MessageHandler = (data: any) => void;

class SocketService {
  private socket: WebSocket | null = null;
  private listeners: Record<string, MessageHandler[]> = {};
  private sessionId: string = '';
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;
  private reconnectDelay = 1000;
  private _connectionState: SocketConnectionState = 'disconnected';
  private _onStateChange: ((state: SocketConnectionState) => void) | null = null;
  private intentionalClose = false;

  get connectionState(): SocketConnectionState {
    return this._connectionState;
  }

  set onStateChange(handler: ((state: SocketConnectionState) => void) | null) {
    this._onStateChange = handler;
  }

  private setConnectionState(state: SocketConnectionState) {
    this._connectionState = state;
    this._onStateChange?.(state);
    this.emit('connectionState', state);
  }

  connect(sessionId: string) {
    if (this.socket && this.sessionId === sessionId && this.socket.readyState === WebSocket.OPEN) {
      return;
    }

    this.intentionalClose = false;
    this.sessionId = sessionId;
    this.cleanup();

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = window.location.host;
    const url = `${protocol}//${host}/api/coding/ws/${sessionId}`;

    this.setConnectionState('connecting');

    try {
      this.socket = new WebSocket(url);
    } catch {
      this.setConnectionState('error');
      this.scheduleReconnect();
      return;
    }

    this.socket.onopen = () => {
      this.reconnectAttempts = 0;
      this.setConnectionState('connected');
      this.emit('connected', { sessionId });
    };

    this.socket.onmessage = (event) => {
      try {
        const parsed = JSON.parse(event.data);
        const { type, data, message } = parsed;
        const payload = data ?? message ?? parsed;
        if (type && this.listeners[type]) {
          this.listeners[type].forEach((cb) => cb(payload));
        }
        if (this.listeners['*']) {
          this.listeners['*'].forEach((cb) => cb({ type, data: payload }));
        }
      } catch {
        // Ignore malformed messages
      }
    };

    this.socket.onerror = () => {
      this.setConnectionState('error');
    };

    this.socket.onclose = () => {
      this.setConnectionState('disconnected');
      if (!this.intentionalClose) {
        this.scheduleReconnect();
      }
    };
  }

  private scheduleReconnect() {
    if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      this.setConnectionState('error');
      return;
    }
    this.reconnectAttempts++;
    const delay = this.reconnectDelay * Math.pow(1.5, this.reconnectAttempts - 1);
    setTimeout(() => {
      if (!this.intentionalClose && this.sessionId) {
        this.connect(this.sessionId);
      }
    }, delay);
  }

  sendMessage(message: string, activeFile: string, autonomous = true) {
    if (this.socket && this.socket.readyState === WebSocket.OPEN) {
      this.socket.send(JSON.stringify({ message, active_file: activeFile, autonomous }));
      return true;
    }
    return false;
  }

  sendCancel() {
    if (this.socket && this.socket.readyState === WebSocket.OPEN) {
      this.socket.send(JSON.stringify({ action: 'cancel' }));
      return true;
    }
    return false;
  }

  on(type: string, callback: MessageHandler) {
    if (!this.listeners[type]) this.listeners[type] = [];
    this.listeners[type].push(callback);
  }

  off(type: string, callback: MessageHandler) {
    if (this.listeners[type]) {
      this.listeners[type] = this.listeners[type].filter((cb) => cb !== callback);
    }
  }

  private emit(type: string, data: any) {
    if (this.listeners[type]) {
      this.listeners[type].forEach((cb) => cb(data));
    }
  }

  private cleanup() {
    if (this.socket) {
      this.socket.onopen = null;
      this.socket.onmessage = null;
      this.socket.onerror = null;
      this.socket.onclose = null;
      if (this.socket.readyState === WebSocket.OPEN || this.socket.readyState === WebSocket.CONNECTING) {
        this.socket.close();
      }
      this.socket = null;
    }
  }

  close() {
    this.intentionalClose = true;
    this.reconnectAttempts = 0;
    this.cleanup();
    this.setConnectionState('disconnected');
  }
}

export const socketService = new SocketService();
