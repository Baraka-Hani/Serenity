export type TravelOffer = {
  id: string
  name: string
  category: 'stay' | 'activity'
  provider: string
  location: string
  price: number | null
  currency: string | null
  url: string
}

export type TravelSearchResponse = {
  offers: TravelOffer[]
}

function isValidDate(value: string): boolean {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(value)) return false
  const parsed = new Date(`${value}T00:00:00.000Z`)
  return Number.isFinite(parsed.getTime()) && parsed.toISOString().slice(0, 10) === value
}

function isTravelOffer(value: unknown): value is TravelOffer {
  if (!value || typeof value !== 'object') return false
  const offer = value as Record<string, unknown>
  let secureUrl = false
  if (typeof offer.url === 'string') {
    try {
      secureUrl = new URL(offer.url).protocol === 'https:'
    } catch {
      secureUrl = false
    }
  }
  return typeof offer.id === 'string'
    && typeof offer.name === 'string'
    && (offer.category === 'stay' || offer.category === 'activity')
    && typeof offer.provider === 'string'
    && typeof offer.location === 'string'
    && (offer.price === null || (typeof offer.price === 'number' && Number.isFinite(offer.price) && offer.price >= 0))
    && (typeof offer.currency === 'string' || offer.currency === null)
    && secureUrl
}

export async function searchTravelOffers(
  endpoint: string,
  token: string,
  location: { latitude: number; longitude: number },
  dates: { checkIn: string; checkOut: string },
): Promise<TravelSearchResponse> {
  if (!endpoint.trim()) throw new Error('Travel search endpoint is not configured.')
  let requestUrl: URL
  try {
    requestUrl = new URL(endpoint, window.location.origin)
  } catch {
    throw new Error('Travel search endpoint is not a valid URL.')
  }
  const isLocalHttp = requestUrl.protocol === 'http:'
    && ['localhost', '127.0.0.1', '[::1]'].includes(requestUrl.hostname)
  if ((requestUrl.protocol !== 'https:' && !isLocalHttp) || requestUrl.username || requestUrl.password) {
    throw new Error('Travel search endpoint must use HTTPS, except for local development.')
  }
  if (!Number.isFinite(location.latitude) || Math.abs(location.latitude) > 90
    || !Number.isFinite(location.longitude) || Math.abs(location.longitude) > 180) {
    throw new Error('Travel search location is invalid.')
  }
  if (!isValidDate(dates.checkIn) || !isValidDate(dates.checkOut) || dates.checkOut <= dates.checkIn) {
    throw new Error('Choose valid travel dates with check-out after check-in.')
  }

  const response = await fetch(requestUrl, {
    method: 'POST',
    headers: {
      Authorization: 'Bearer ' + token,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ location, ...dates, categories: ['stay', 'activity'] }),
  })

  if (!response.ok) {
    if (response.status === 401 || response.status === 403) {
      throw new Error('Travel search authorization failed. Sign in again or check backend access.')
    }
    throw new Error(`Travel search failed (${response.status}). Please try again later.`)
  }

  const result: unknown = await response.json()
  if (!result || typeof result !== 'object' || !Array.isArray((result as Record<string, unknown>).offers)) {
    throw new Error('Travel search returned an invalid response.')
  }
  const offers = (result as { offers: unknown[] }).offers
  if (!offers.every(isTravelOffer)) throw new Error('Travel search returned malformed offer data.')
  return { offers }
}
