import { getPrivateJson, postPrivateJson, type PaymentResult } from './api';

export type PaymentQuote = {
  booking_reference: string;
  amount_gnf: number;
  currency: 'GNF' | string;
  permit_category?: string | null;
  attempt_number?: number | null;
  source: 'server_tariff' | string;
};

export function getPaymentQuote(bookingReference: string): Promise<PaymentQuote> {
  return getPrivateJson<PaymentQuote>(`/api/v1/payments/quote/${encodeURIComponent(bookingReference)}`);
}

/**
 * Crée le paiement sans envoyer de prix client : le backend recalcule toujours
 * le montant applicable à partir de la réservation/catégorie/tentative.
 */
export function createServerPricedPayment(payload: {
  booking_reference: string;
  provider: string;
  phone: string;
}): Promise<PaymentResult> {
  return postPrivateJson<PaymentResult>('/api/v1/payments', payload);
}
