export type ProductType = 'STARS_FIXED' | 'STARS_CUSTOM' | 'PREMIUM_MONTHS' | 'GIFT';

export type OrderStatus =
  | 'CREATED'
  | 'AWAITING_PAYMENT'
  | 'PAID'
  | 'FULFILLING'
  | 'COMPLETED'
  | 'FAILED'
  | 'REFUND_PENDING'
  | 'REFUNDED'
  | 'CANCELLED';

export type PaymentProvider = 'CRYPTOBOT' | 'LAVAPAY';

export interface Product {
  id: string;
  sku: string;
  name: string;
  description?: string;
  product_type: ProductType;
  base_price_ton: number;
  min_quantity?: number;
  max_quantity?: number;
  default_quantity: number;
  is_active: boolean;
  sort_order: number;
  estimated_price_rub?: number;
}

export interface Category {
  id: string;
  slug: string;
  name: string;
  description?: string;
  icon?: string;
  margin_percent: number;
  is_active: boolean;
  sort_order: number;
  products: Product[];
}

export interface OrderEvent {
  id: string;
  from_status?: OrderStatus;
  to_status: OrderStatus;
  event_type: string;
  details?: Record<string, any>;
  created_at: string;
}

export interface Order {
  id: string;
  order_number: number;
  user_id: number;
  product_id: string;
  quantity: number;
  recipient_username: string;
  is_gift: boolean;
  status: OrderStatus;
  payment_provider: PaymentProvider;
  payment_invoice_id?: string;
  payment_url?: string;
  fiat_amount: number;
  fiat_currency: string;
  crypto_amount?: number;
  crypto_currency?: string;
  ton_rate_applied: number;
  expires_at: string;
  created_at: string;
  events: OrderEvent[];
}

export interface User {
  id: number;
  first_name: string;
  last_name?: string;
  username?: string;
  is_premium: boolean;
  is_blocked: boolean;
  is_admin: boolean;
}
