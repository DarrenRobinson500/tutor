import { apiFetchJson } from '../utils/apiFetch';
import { Payment, PaymentCreate } from '../types/Payment';

export function usePaymentApi() {
  const listPayments = (): Promise<Payment[]> =>
    apiFetchJson('/api/payments/');

  const getPayment = (id: number): Promise<Payment> =>
    apiFetchJson(`/api/payments/${id}/`);

  const createPayment = (payload: PaymentCreate): Promise<Payment> =>
    apiFetchJson('/api/payments/', { method: 'POST', body: JSON.stringify(payload) });

  const updatePayment = (id: number, payload: Partial<PaymentCreate>): Promise<Payment> =>
    apiFetchJson(`/api/payments/${id}/`, { method: 'PATCH', body: JSON.stringify(payload) });

  const deletePayment = (id: number): Promise<void> =>
    apiFetchJson(`/api/payments/${id}/`, { method: 'DELETE' });

  return { listPayments, getPayment, createPayment, updatePayment, deletePayment };
}
