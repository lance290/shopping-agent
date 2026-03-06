export interface Deal {
  id: number;
  title: string;
  price: number | null;
  source: string;
  url: string | null;
  image_url: string | null;
  is_selected?: boolean;
}

export interface Swap {
  id: number;
  title: string;
  price: number | null;
  source: string;
  url: string | null;
  image_url: string | null;
  savings_vs_first: number | null;
  is_selected?: boolean;
}

export interface CouponBadge {
  swap_id: number;
  savings_cents: number;
  savings_display: string;
  brand_name: string | null;
  product_name: string;
  url: string | null;
  is_sponsored?: boolean;
}

export interface ListItem {
  id: number;
  title: string;
  status: string;
  created_at: string | null;
  deals: Deal[];
  swaps: Swap[];
  lowest_price: number | null;
  deal_count: number;
  department?: string | null;
  brand?: string | null;
  size?: string | null;
  quantity?: string | null;
  origin_channel?: string | null;
  origin_user_id?: number | null;
  like_count?: number;
  user_liked?: boolean;
  comment_count?: number;
  coupon?: CouponBadge | null;
}

export interface PopList {
  project_id: number;
  title: string;
  shopping_mode?: boolean;
  items: ListItem[];
}

export type TabType = 'deals' | 'swaps';

export interface ItemLikeState {
  liked: boolean;
  count: number;
}

export interface ItemComment {
  id: number;
  user_name: string;
  text: string;
  created_at: string | null;
}
