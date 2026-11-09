import { TravelMetadata } from './travelMetadata'

export type TravelRecord = Omit<TravelMetadata, 'latitude' | 'longitude'> & {
  id: string
  savedAt: string
}

export type AlbumMedia = {
  name: string
  contentType: string
  path: string
}

export type Album = {
  id: string
  ownerId?: string
  title: string
  destination?: string
  tripDescription?: string
  tripStartDate?: string
  tripEndDate?: string
  createdAt: string
  clipCount: number
  regions: string[]
  primary: string
  secondary: string
  searchLocation?: { latitude: number; longitude: number }
  media?: AlbumMedia[]
}
