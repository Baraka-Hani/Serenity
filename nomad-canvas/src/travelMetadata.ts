export type TravelMetadata = {
  region: string
  timezone: string
  capturedAt: string | null
  latitude: number
  longitude: number
}

const MAX_SCAN_BYTES = 4 * 1024 * 1024

function regionFromCoordinates(latitude: number, longitude: number): string {
  if (latitude > 72 || latitude < -55) return 'Polar region'
  if (longitude >= -170 && longitude <= -30 && latitude >= 5 && latitude <= 85) return 'North America'
  if (longitude >= -85 && longitude <= -30 && latitude >= -60 && latitude < 15) return 'South America'
  if (longitude >= -25 && longitude <= 45 && latitude >= 34 && latitude <= 72) return 'Europe'
  if (longitude >= -20 && longitude <= 55 && latitude >= -36 && latitude < 38) return 'Africa'
  if (longitude >= 25 && longitude <= 180 && latitude >= -10 && latitude <= 82) return 'Asia'
  if (longitude >= 110 && longitude <= 180 && latitude >= -50 && latitude < 0) return 'Oceania'
  return 'Remote region'
}

function timezoneFromLongitude(longitude: number): string {
  const offsetMinutes = Math.max(-720, Math.min(720, Math.round(longitude / 7.5) * 30))
  const sign = offsetMinutes < 0 ? '-' : '+'
  const absoluteMinutes = Math.abs(offsetMinutes)
  const hours = String(Math.floor(absoluteMinutes / 60)).padStart(2, '0')
  const minutes = String(absoluteMinutes % 60).padStart(2, '0')
  return `UTC${sign}${hours}:${minutes} (approx.)`
}

function findCoordinates(text: string): { latitude: number; longitude: number } | null {
  const iso6709 = /([+-]\d{2}(?:\.\d+)?)([+-]\d{3}(?:\.\d+)?)(?:[+-]\d+(?:\.\d+)?)?\//g
  for (const match of text.matchAll(iso6709)) {
    const latitude = Number(match[1])
    const longitude = Number(match[2])
    if (Math.abs(latitude) <= 90 && Math.abs(longitude) <= 180) return { latitude, longitude }
  }
  return null
}

function findCaptureDate(text: string): string | null {
  const datePattern = /\b(?:19|20)\d{2}-\d{2}-\d{2}(?:[T ]\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:?\d{2})?)?/g
  for (const match of text.matchAll(datePattern)) {
    const timestamp = Date.parse(match[0])
    if (Number.isFinite(timestamp)) return match[0]
  }
  return null
}

export async function travelMetadataFromVideo(file: File): Promise<TravelMetadata | null> {
  const head = await file.slice(0, MAX_SCAN_BYTES).arrayBuffer()
  const tailStart = Math.max(MAX_SCAN_BYTES, file.size - MAX_SCAN_BYTES)
  const tail = file.size > MAX_SCAN_BYTES ? await file.slice(tailStart).arrayBuffer() : null
  const decoder = new TextDecoder()
  const text = decoder.decode(head) + (tail ? `\u0000${decoder.decode(tail)}` : '')
  const coordinates = findCoordinates(text)

  if (!coordinates) return null

  return {
    region: regionFromCoordinates(coordinates.latitude, coordinates.longitude),
    timezone: timezoneFromLongitude(coordinates.longitude),
    capturedAt: findCaptureDate(text),
    latitude: coordinates.latitude,
    longitude: coordinates.longitude,
  }
}
