function secureEndpoint(endpoint: string): URL {
  if (!endpoint.trim()) throw new Error('This payment service is not configured yet.')
  let url: URL
  try {
    url = new URL(endpoint, window.location.origin)
  } catch {
    throw new Error('The payment service URL is invalid.')
  }
  const localHttp = url.protocol === 'http:' && ['localhost', '127.0.0.1', '[::1]'].includes(url.hostname)
  if ((url.protocol !== 'https:' && !localHttp) || url.username || url.password) {
    throw new Error('Payment services must use HTTPS, except during local development.')
  }
  return url
}

async function stripeUrlFromResponse(response: Response): Promise<string> {
  if (!response.ok) {
    if (response.status === 401 || response.status === 403) {
      throw new Error('Your sign-in has expired or you are not authorized for this payment action.')
    }
    throw new Error(`Payment service failed (${response.status}). Please try again later.`)
  }
  const body: unknown = await response.json()
  const url = body && typeof body === 'object' ? (body as Record<string, unknown>).url : null
  if (typeof url !== 'string') throw new Error('Payment service returned an invalid redirect.')
  let redirect: URL
  try {
    redirect = new URL(url)
  } catch {
    throw new Error('Payment service returned an invalid redirect.')
  }
  if (redirect.protocol !== 'https:' || redirect.hostname !== 'checkout.stripe.com' && redirect.hostname !== 'connect.stripe.com') {
    throw new Error('Payment service returned an untrusted Stripe URL.')
  }
  return redirect.toString()
}

export async function startCreatorPayoutSetup(endpoint: string, token: string): Promise<string> {
  const response = await fetch(secureEndpoint(endpoint), {
    method: 'POST',
    headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
    body: JSON.stringify({}),
  })
  return stripeUrlFromResponse(response)
}

export async function createTripCheckout(
  endpoint: string,
  token: string,
  request: { tripId: string; offerIds: string[]; checkIn: string; checkOut: string },
): Promise<string> {
  if (!request.tripId || !request.offerIds.length || new Set(request.offerIds).size !== request.offerIds.length) {
    throw new Error('Choose at least one unique trip item before checkout.')
  }
  if (!/^\d{4}-\d{2}-\d{2}$/.test(request.checkIn)
    || !/^\d{4}-\d{2}-\d{2}$/.test(request.checkOut)
    || request.checkOut <= request.checkIn) {
    throw new Error('Choose valid trip dates before checkout.')
  }
  const response = await fetch(secureEndpoint(endpoint), {
    method: 'POST',
    headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
    body: JSON.stringify(request),
  })
  return stripeUrlFromResponse(response)
}
