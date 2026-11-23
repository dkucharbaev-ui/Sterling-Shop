import { Category, Order, User } from '../types';

const API_BASE = '/api/v1';

class ApiClient {
  private token: string | null = null;

  constructor() {
    this.token = sessionStorage.getItem('psycho_jwt');
  }

  setToken(token: string) {
    this.token = token;
    sessionStorage.setItem('psycho_jwt', token);
  }

  private async request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
      ...(options.headers as Record<string, string>),
    };

    if (this.token) {
      headers['Authorization'] = `Bearer ${this.token}`;
    }

    const response = await fetch(`${API_BASE}${endpoint}`, {
      ...options,
      headers,
    });

    if (response.status === 401 && this.token) {
      // Token expired, clear and attempt re-auth
      this.token = null;
      sessionStorage.removeItem('psycho_jwt');
    }

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.detail || `Request failed with status ${response.status}`);
    }

    return response.json();
  }

  async authenticate(initData: string): Promise<{ access_token: string; user: User }> {
    const res = await this.request<{ access_token: string; user: User }>('/auth/telegram', {
      method: 'POST',
      body: JSON.stringify({ init_data: initData }),
    });
    this.setToken(res.access_token);
    return res;
  }

  async getMe(): Promise<User> {
    return this.request<User>('/auth/me');
  }

  async getCatalog(): Promise<Category[]> {
    return this.request<Category[]>('/catalog');
  }

  async calculateStars(quantity: number, currency = 'RUB'): Promise<{
    quantity: number;
    price: number;
    currency: string;
    price_per_star: number;
    ton_rate_applied: number;
  }> {
    return this.request('/catalog/stars/calculate', {
      method: 'POST',
      body: JSON.stringify({ quantity, currency }),
    });
  }

  async validateRecipient(username: string, productId?: string): Promise<{
    is_valid: bool;
    clean_username: string;
    has_active_premium: boolean;
    error_message?: string;
  }> {
    return this.request('/catalog/recipient/validate', {
      method: 'POST',
      body: JSON.stringify({ username, product_id: productId }),
    });
  }

  async createOrder(payload: {
    product_id: string;
    quantity: number;
    recipient_username: string;
    payment_provider: 'CRYPTOBOT' | 'LAVAPAY';
    currency?: string;
    is_gift?: boolean;
  }): Promise<Order> {
    return this.request<Order>('/orders', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  }

  async getMyOrders(): Promise<Order[]> {
    return this.request<Order[]>('/orders');
  }

  async getOrderStatus(orderId: string): Promise<{ order_id: string; status: string; payment_url?: string }> {
    return this.request(`/orders/${orderId}/status`);
  }
}

export const api = new ApiClient();
