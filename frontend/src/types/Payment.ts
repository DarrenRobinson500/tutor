export interface Payment {
  id: number;
  amount_paid: string;
  amount_platform: string;
  amount_distributor: string;
  amount_tutor: string;
  focus_area: string;
  date_tuition: string;   // ISO date: YYYY-MM-DD
  date_debit: string | null;
  date_credit: string | null;
  account_paid: number | null;
  account_platform: number | null;
  account_distributor: number | null;
  account_tutor: number | null;
}

export interface PaymentCreate {
  amount_paid: string;
  amount_platform: string;
  amount_distributor: string;
  amount_tutor: string;
  focus_area: string;
  date_tuition: string;
  date_debit?: string | null;
  date_credit?: string | null;
  account_paid?: number | null;
  account_platform?: number | null;
  account_distributor?: number | null;
  account_tutor?: number | null;
}
