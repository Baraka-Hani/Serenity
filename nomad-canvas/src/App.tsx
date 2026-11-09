import { ChangeEvent, CSSProperties, DragEvent, FormEvent, useEffect, useRef, useState } from 'react'
import { ArrowDown, ArrowLeft, ArrowUpRight, CalendarDays, Check, Compass, Film, Globe2, LockKeyhole, Mail, MapPin, Menu, Pause, Play, Plus, Sparkles, UserRound, Users, X } from 'lucide-react'
import { defaultTheme, Theme, themeFromVideo } from './theme'
import { TravelMetadata, travelMetadataFromVideo } from './travelMetadata'
import type { Album, TravelRecord } from './models'
import { auth, authPersistenceReady, firebaseConfigured, mediaStorageConfigured } from './firebase'
import { createUserWithEmailAndPassword, GoogleAuthProvider, onAuthStateChanged, signInWithEmailAndPassword, signInWithPopup, signOut } from 'firebase/auth'
import type { User } from 'firebase/auth'
import { createUserAlbum, loadAlbumMedia, loadPublishedTrips, loadUserAlbums, loadUserTravelRecords, saveUserTravelRecords } from './cloudData'
import { searchTravelOffers } from './travelSearch'
import type { TravelOffer } from './travelSearch'
import { loadLocalAlbumMedia, saveLocalAlbumMedia } from './localMedia'
import { createTripCheckout, startCreatorPayoutSetup } from './tripPayments'

type Clip = {
  id: string
  file: File
  url: string
  status: 'analyzing' | 'ready' | 'error'
  travelStatus: 'analyzing' | 'found' | 'missing' | 'error'
  travel?: TravelMetadata
  archivedFor?: string
}

type FeedCategory = 'discover' | 'create' | 'friends'

const storagePrefix = 'roam-make-travel-v1:'
const albumStoragePrefix = 'roam-make-albums-v1:'
const activeAccountKey = 'roam-make-active-account'

function normalizeEmail(email: string): string {
  return email.trim().toLowerCase()
}

function isAccountEmail(email: string): boolean {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)
}

function isTravelRecord(value: unknown): value is TravelRecord {
  if (!value || typeof value !== 'object') return false
  const record = value as Record<string, unknown>
  return typeof record.id === 'string'
    && typeof record.region === 'string'
    && typeof record.timezone === 'string'
    && (typeof record.capturedAt === 'string' || record.capturedAt === null)
    && typeof record.savedAt === 'string'
}

function readTravelRecords(email: string): TravelRecord[] {
  const saved = localStorage.getItem(`${storagePrefix}${encodeURIComponent(email)}`)
  if (!saved) return []
  const parsed: unknown = JSON.parse(saved)
  if (!Array.isArray(parsed) || !parsed.every(isTravelRecord)) {
    throw new Error('The saved travel archive has an unexpected format.')
  }
  return parsed
}

function isSearchLocation(value: unknown): value is { latitude: number; longitude: number } {
  if (!value || typeof value !== 'object') return false
  const location = value as Record<string, unknown>
  return typeof location.latitude === 'number'
    && Number.isFinite(location.latitude)
    && Math.abs(location.latitude) <= 90
    && typeof location.longitude === 'number'
    && Number.isFinite(location.longitude)
    && Math.abs(location.longitude) <= 180
}

function isAlbum(value: unknown): value is Album {
  if (!value || typeof value !== 'object') return false
  const album = value as Record<string, unknown>
  return typeof album.id === 'string'
    && (album.ownerId === undefined || typeof album.ownerId === 'string')
    && typeof album.title === 'string'
    && (album.destination === undefined || typeof album.destination === 'string')
    && (album.tripDescription === undefined || typeof album.tripDescription === 'string')
    && (album.tripStartDate === undefined || typeof album.tripStartDate === 'string')
    && (album.tripEndDate === undefined || typeof album.tripEndDate === 'string')
    && typeof album.createdAt === 'string'
    && typeof album.clipCount === 'number'
    && Array.isArray(album.regions)
    && album.regions.every((region) => typeof region === 'string')
    && typeof album.primary === 'string'
    && typeof album.secondary === 'string'
    && (album.searchLocation === undefined || isSearchLocation(album.searchLocation))
    && (album.media === undefined || (
      Array.isArray(album.media)
      && album.media.every((media) => Boolean(media)
        && typeof media === 'object'
        && typeof (media as Record<string, unknown>).name === 'string'
        && typeof (media as Record<string, unknown>).contentType === 'string'
        && typeof (media as Record<string, unknown>).path === 'string')
    ))
}

function readAlbums(email: string): Album[] {
  const saved = localStorage.getItem(`${albumStoragePrefix}${encodeURIComponent(email)}`)
  if (!saved) return []
  const parsed: unknown = JSON.parse(saved)
  if (!Array.isArray(parsed) || !parsed.every(isAlbum)) {
    throw new Error('The saved album feed has an unexpected format.')
  }
  return parsed
}

export default function App() {
  const [theme, setTheme] = useState<Theme>(defaultTheme)
  const [clips, setClips] = useState<Clip[]>([])
  const [user, setUser] = useState<User | null>(null)
  const [authLoading, setAuthLoading] = useState(firebaseConfigured)
  const [authEmail, setAuthEmail] = useState('')
  const [authPassword, setAuthPassword] = useState('')
  const [authMode, setAuthMode] = useState<'signin' | 'signup'>('signin')
  const [authMessage, setAuthMessage] = useState('')
  const [albums, setAlbums] = useState<Album[]>([])
  const [accountDataLoading, setAccountDataLoading] = useState(firebaseConfigured)
  const [accountEmail, setAccountEmail] = useState('')
  const [travelRecords, setTravelRecords] = useState<TravelRecord[]>([])
  const [travelMessage, setTravelMessage] = useState('')
  const [albumMessage, setAlbumMessage] = useState('')
  const [albumTitle, setAlbumTitle] = useState('')
  const [draftAlbum, setDraftAlbum] = useState<Album | null>(null)
  const [savingAlbum, setSavingAlbum] = useState(false)
  const [publishConfirmed, setPublishConfirmed] = useState(false)
  const [tripDestination, setTripDestination] = useState('')
  const [tripDescription, setTripDescription] = useState('')
  const [tripStartDate, setTripStartDate] = useState('')
  const [tripEndDate, setTripEndDate] = useState('')
  const [screen, setScreen] = useState<'landing' | 'feed' | 'profile'>('landing')
  const [feedCategory, setFeedCategory] = useState<FeedCategory>('discover')
  const [selectedAlbum, setSelectedAlbum] = useState<Album | null>(null)
  const [albumMedia, setAlbumMedia] = useState<Array<{ name: string; contentType: string; path: string; url: string }>>([])
  const [albumMediaLoading, setAlbumMediaLoading] = useState(false)
  const [travelOffers, setTravelOffers] = useState<TravelOffer[]>([])
  const [selectedOfferIds, setSelectedOfferIds] = useState<string[]>([])
  const [searchingOffers, setSearchingOffers] = useState(false)
  const [checkoutLoading, setCheckoutLoading] = useState(false)
  const [checkoutMessage, setCheckoutMessage] = useState('')
  const [payoutMessage, setPayoutMessage] = useState('')
  const [offerMessage, setOfferMessage] = useState('')
  const [checkIn, setCheckIn] = useState(() => {
    const date = new Date()
    date.setDate(date.getDate() + 7)
    return date.toISOString().slice(0, 10)
  })
  const [checkOut, setCheckOut] = useState(() => {
    const date = new Date()
    date.setDate(date.getDate() + 10)
    return date.toISOString().slice(0, 10)
  })
  const [dragging, setDragging] = useState(false)
  const [playing, setPlaying] = useState(true)
  const [studioOpen, setStudioOpen] = useState(false)
  const inputRef = useRef<HTMLInputElement>(null)
  const previousUserId = useRef<string | null>(null)
  const profileReturnScreen = useRef<'landing' | 'feed'>('landing')

  const submitAuth = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    if (!auth) {
      setAuthMessage('Firebase is not configured. Add the Firebase web app settings to .env.local.')
      return
    }
    try {
      await authPersistenceReady
      if (authMode === 'signup') await createUserWithEmailAndPassword(auth, authEmail.trim(), authPassword)
      else await signInWithEmailAndPassword(auth, authEmail.trim(), authPassword)
      setAuthMessage('')
    } catch (error) {
      setAuthMessage(error instanceof Error ? error.message : 'Authentication failed. Please try again.')
    }
  }

  const signInWithGoogle = async () => {
    if (!auth) return
    try {
      await authPersistenceReady
      await signInWithPopup(auth, new GoogleAuthProvider())
      setAuthMessage('')
    } catch (error) {
      setAuthMessage(error instanceof Error ? error.message : 'Google sign-in failed. Please try again.')
    }
  }

  const signOutCurrentUser = async () => {
    if (!auth) return
    try {
      await signOut(auth)
      setScreen('landing')
      clips.forEach((clip) => URL.revokeObjectURL(clip.url))
      setClips([])
    } catch (error) {
      setAlbumMessage(error instanceof Error ? error.message : 'Could not sign out.')
    }
  }

  const searchForTravel = async (album: Album) => {
    const endpoint = import.meta.env.VITE_TRAVEL_SEARCH_URL
    if (!user) {
      setOfferMessage('Sign in with Firebase to search travel availability.')
      return
    }
    if (!endpoint) {
      setOfferMessage('Travel search is not connected yet. Configure the backend endpoint to search stays and activities.')
      return
    }
    if (!album.searchLocation) {
      setOfferMessage('This album has no embedded location to search around.')
      return
    }
    setSearchingOffers(true)
    setOfferMessage('')
    setTravelOffers([])
    setSelectedOfferIds([])
    setCheckoutMessage('')
    try {
      if (checkOut <= checkIn) {
        setOfferMessage('Choose a check-out date after the check-in date.')
        return
      }
      const result = await searchTravelOffers(endpoint, await user.getIdToken(), album.searchLocation, { checkIn, checkOut })
      if (auth?.currentUser?.uid !== user.uid) return
      setTravelOffers(result.offers)
      setSelectedOfferIds([])
      setOfferMessage(result.offers.length ? `${result.offers.length} options found near this journey.` : 'No available options were returned for this location.')
    } catch (error) {
      setOfferMessage(error instanceof Error ? error.message : 'Travel search failed. Please try again.')
    } finally {
      setSearchingOffers(false)
    }
  }

  const startCheckout = async () => {
    const endpoint = import.meta.env.VITE_TRIP_CHECKOUT_URL
    if (!user || !selectedAlbum) {
      setCheckoutMessage('Sign in and open a published trip before checkout.')
      return
    }
    const selectedOffers = travelOffers.filter((offer) => selectedOfferIds.includes(offer.id))
    if (!selectedOffers.length || selectedOffers.some((offer) => offer.price === null || !offer.currency)) {
      setCheckoutMessage('Select trip items with a listed price and currency before checkout.')
      return
    }
    if (new Set(selectedOffers.map((offer) => offer.currency)).size !== 1) {
      setCheckoutMessage('Select trip items in a single currency to continue.')
      return
    }
    setCheckoutLoading(true)
    setCheckoutMessage('')
    try {
      const url = await createTripCheckout(endpoint ?? '', await user.getIdToken(), {
        tripId: selectedAlbum.id,
        offerIds: selectedOffers.map((offer) => offer.id),
        checkIn,
        checkOut,
      })
      if (auth?.currentUser?.uid !== user.uid) return
      window.location.assign(url)
    } catch (error) {
      setCheckoutMessage(error instanceof Error ? error.message : 'Could not start checkout.')
    } finally {
      setCheckoutLoading(false)
    }
  }

  const connectCreatorPayouts = async () => {
    const endpoint = import.meta.env.VITE_STRIPE_CONNECT_URL
    if (!user) {
      setPayoutMessage('Sign in to set up creator payouts.')
      return
    }
    setPayoutMessage('')
    try {
      const url = await startCreatorPayoutSetup(endpoint ?? '', await user.getIdToken())
      if (auth?.currentUser?.uid === user.uid) window.location.assign(url)
    } catch (error) {
      setPayoutMessage(error instanceof Error ? error.message : 'Could not start Stripe payout setup.')
    }
  }

  useEffect(() => {
    if (auth) {
      const configuredAuth = auth
      let cancelled = false
      let unsubscribe: (() => void) | undefined
      void authPersistenceReady
        .then(() => {
          if (cancelled) return
          unsubscribe = onAuthStateChanged(configuredAuth, (nextUser) => {
            setUser(nextUser)
            setAccountEmail(nextUser?.email ?? '')
            setAuthMessage('')
            if (nextUser) {
              setScreen('feed')
              setFeedCategory('discover')
              setSelectedAlbum(null)
            }
            setAuthLoading(false)
          }, (error) => {
            setAuthMessage(`Could not check sign-in status: ${error.message}`)
            setAuthLoading(false)
          })
        })
        .catch((error: unknown) => {
          if (cancelled) return
          setAuthMessage(`Could not restore your saved sign-in: ${error instanceof Error ? error.message : 'Authentication persistence is unavailable.'}`)
          setAuthLoading(false)
        })
      return () => {
        cancelled = true
        unsubscribe?.()
      }
    }
    setAuthLoading(false)
    try {
      setAccountEmail(localStorage.getItem(activeAccountKey) ?? '')
    } catch {
      setTravelMessage('This browser is blocking local storage. Travel details cannot be saved.')
    }
  }, [])

  useEffect(() => {
    const currentUserId = user?.uid ?? null
    if (previousUserId.current && previousUserId.current !== currentUserId) {
      clips.forEach((clip) => URL.revokeObjectURL(clip.url))
      setClips([])
      setSelectedAlbum(null)
      setAlbumMedia([])
      setTravelOffers([])
      setOfferMessage('')
      setScreen('landing')
    }
    previousUserId.current = currentUserId
  }, [user, clips])

  useEffect(() => {
    if (firebaseConfigured) {
      if (!user) {
        setTravelRecords([])
        setAlbums([])
        setAccountDataLoading(false)
        return
      }
      let cancelled = false
      setAccountDataLoading(true)
      void Promise.all([loadUserAlbums(user), loadPublishedTrips(), loadUserTravelRecords(user)])
        .then(([ownedAlbums, publishedTrips, loadedTravel]) => {
          if (cancelled) return
          const visibleAlbums = new Map<string, Album>()
          ownedAlbums.forEach((album) => visibleAlbums.set(album.id, album))
          publishedTrips.forEach((album) => visibleAlbums.set(album.id, album))
          setAlbums([...visibleAlbums.values()].sort((left, right) => right.createdAt.localeCompare(left.createdAt)))
          setTravelRecords(loadedTravel)
          setAccountDataLoading(false)
        })
        .catch((error: unknown) => {
          if (cancelled) return
          const message = error instanceof Error ? error.message : 'Unknown cloud data error.'
          setAlbumMessage(`Could not load your cloud account data: ${message}`)
          setAccountDataLoading(false)
        })
      return () => { cancelled = true }
    }

    const email = normalizeEmail(accountEmail)
    if (!isAccountEmail(email)) {
      setTravelRecords([])
      setAlbums([])
      return
    }
    try {
      localStorage.setItem(activeAccountKey, email)
      setTravelRecords(readTravelRecords(email))
      setAlbums(readAlbums(email))
      setTravelMessage('')
      setAlbumMessage('')
    } catch {
      setTravelRecords([])
      setAlbums([])
      setTravelMessage('Could not read this local archive. Check browser storage settings.')
      setAlbumMessage('Could not read this local album feed. Check browser storage settings.')
    }
  }, [accountEmail, user])

  useEffect(() => {
    const selectedMedia = selectedAlbum?.media
    setAlbumMedia([])
    if (!selectedAlbum || !selectedMedia?.length) {
      setAlbumMediaLoading(false)
      return
    }
    let cancelled = false
    setAlbumMediaLoading(true)
    const mediaRequest = user
      ? loadAlbumMedia(user, selectedMedia)
      : loadLocalAlbumMedia(selectedAlbum.id)
    void mediaRequest
      .then((media) => {
        if (cancelled) {
          media.forEach((item) => URL.revokeObjectURL(item.url))
          return
        }
        setAlbumMedia(media)
        setAlbumMediaLoading(false)
      })
      .catch((error: unknown) => {
        if (!cancelled) {
          setAlbumMediaLoading(false)
          setOfferMessage(`Could not load album videos: ${error instanceof Error ? error.message : 'Unknown storage error.'}`)
        }
      })
    return () => { cancelled = true }
  }, [user, selectedAlbum])

  useEffect(() => () => {
    albumMedia.forEach((media) => URL.revokeObjectURL(media.url))
  }, [albumMedia])

  useEffect(() => {
    const email = normalizeEmail(accountEmail)
    if (firebaseConfigured && !user) return
    if (!firebaseConfigured && !isAccountEmail(email)) return

    const foundRecords = clips.flatMap((clip) => {
      const owner = firebaseConfigured ? user?.uid : email
      if (clip.travelStatus !== 'found' || !clip.travel || clip.archivedFor === owner) return []
      return [{
        id: clip.id,
        region: clip.travel.region,
        timezone: clip.travel.timezone,
        capturedAt: clip.travel.capturedAt,
        savedAt: new Date().toISOString(),
      }]
    })
    if (!foundRecords.length) return

    if (firebaseConfigured && user) {
      void saveUserTravelRecords(user, foundRecords)
        .then(() => {
          if (auth?.currentUser?.uid !== user.uid) return
          const savedIds = new Set(foundRecords.map((record) => record.id))
          setClips((current) => current.map((clip) => savedIds.has(clip.id) ? { ...clip, archivedFor: user.uid } : clip))
          setTravelRecords((current) => [...foundRecords, ...current.filter((record) => !savedIds.has(record.id))])
          setTravelMessage(`${foundRecords.length} approximate location ${foundRecords.length === 1 ? 'entry' : 'entries'} saved to your account.`)
        })
        .catch((error: unknown) => {
          if (auth?.currentUser?.uid !== user.uid) return
          setTravelMessage(`Could not save travel metadata: ${error instanceof Error ? error.message : 'Unknown cloud error.'}`)
        })
      return
    }

    try {
      const existing = readTravelRecords(email)
      const newRecords = foundRecords.filter((record) => !existing.some((item) => item.id === record.id))
      if (!newRecords.length) return
      const updated = [...newRecords, ...existing]
      localStorage.setItem(`${storagePrefix}${encodeURIComponent(email)}`, JSON.stringify(updated))
      setTravelRecords(updated)
      const savedIds = new Set(newRecords.map((record) => record.id))
      setClips((current) => current.map((clip) => savedIds.has(clip.id) ? { ...clip, archivedFor: email } : clip))
      setTravelMessage(`${newRecords.length} location ${newRecords.length === 1 ? 'entry' : 'entries'} saved to this device.`)
    } catch {
      setTravelMessage('Location details were found, but could not be saved. Check browser storage settings.')
    }
  }, [accountEmail, clips, user])

  const openFeed = (category: FeedCategory = 'discover') => {
    setFeedCategory(category)
    setSelectedAlbum(null)
    setScreen('feed')
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }

  const openProfile = () => {
    if (screen !== 'profile') profileReturnScreen.current = screen
    setScreen('profile')
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }

  const closeProfile = () => {
    setScreen(profileReturnScreen.current)
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }

  const openAlbum = (album: Album) => {
    setSelectedAlbum(album)
    setCheckIn(album.tripStartDate || checkIn)
    setCheckOut(album.tripEndDate || checkOut)
    setTravelOffers([])
    setSelectedOfferIds([])
    setOfferMessage('')
    setCheckoutMessage('')
  }

  const saveAlbum = async (album: Album, files: File[]): Promise<Album | null> => {
    if (firebaseConfigured) {
      if (!mediaStorageConfigured) {
        setAlbumMessage('Video publishing is unavailable without Firebase Storage. This no-billing test can still use sign-in and saved travel metadata.')
        return null
      }
      if (!user) {
        setAlbumMessage('Sign in before saving an album to your account.')
        return null
      }
      try {
        const saved = await createUserAlbum(user, album, files)
        if (auth?.currentUser?.uid !== user.uid) return null
        const published = { ...saved, ownerId: user.uid }
        setAlbums((current) => [published, ...current.filter((item) => item.id !== published.id)])
        setAlbumMessage('Collection published to all signed-in Roam / Make users.')
        return published
      } catch (error) {
        setAlbumMessage(error instanceof Error ? error.message : 'Could not save this album to your account.')
        return null
      }
    }

    const email = normalizeEmail(accountEmail)
    if (!isAccountEmail(email)) {
      setAlbumMessage('Enter a valid email to save this album and its videos to this device.')
      return null
    }
    try {
      const media = await saveLocalAlbumMedia(album.id, files)
      const savedAlbum = { ...album, media }
      const updated = [savedAlbum, ...readAlbums(email).filter((item) => item.id !== album.id)]
      localStorage.setItem(`${albumStoragePrefix}${encodeURIComponent(email)}`, JSON.stringify(updated))
      setAlbums(updated)
      setAlbumMessage('Album and videos saved to this device.')
      return savedAlbum
    } catch (error) {
      setAlbumMessage(`Album could not be saved: ${error instanceof Error ? error.message : 'Check browser storage settings.'}`)
      return null
    }
  }

  const saveDraftAlbum = async () => {
    if (!draftAlbum || !clips.length || savingAlbum) return
    if (clips.some((clip) => clip.status === 'analyzing' || clip.travelStatus === 'analyzing')) {
      setAlbumMessage('Wait for video analysis to finish before saving.')
      return
    }
    if ((tripStartDate || tripEndDate)
      && (!tripStartDate || !tripEndDate || tripEndDate <= tripStartDate)) {
      setAlbumMessage('Enter both trip dates and choose a trip end date after the start date.')
      return
    }
    if (firebaseConfigured && !publishConfirmed) {
      setAlbumMessage('Confirm that this collection and its videos can be seen by all signed-in users.')
      return
    }
    setSavingAlbum(true)
    setAlbumMessage('Saving album and videos…')
    try {
      const albumToSave: Album = {
        ...draftAlbum,
        title: albumTitle.trim() || draftAlbum.title,
        destination: tripDestination.trim(),
        tripDescription: tripDescription.trim(),
        tripStartDate,
        tripEndDate,
      }
      const savedAlbum = await saveAlbum(albumToSave, clips.map((clip) => clip.file))
      if (!savedAlbum) return
      clips.forEach((clip) => URL.revokeObjectURL(clip.url))
      setClips([])
      setDraftAlbum(null)
      setStudioOpen(false)
      setAlbumTitle('')
      setTripDestination('')
      setTripDescription('')
      setTripStartDate('')
      setTripEndDate('')
      setPublishConfirmed(false)
      setFeedCategory('discover')
      setSelectedAlbum(savedAlbum)
      setCheckIn(savedAlbum.tripStartDate || checkIn)
      setCheckOut(savedAlbum.tripEndDate || checkOut)
      setTravelOffers([])
      setOfferMessage('')
      setScreen('feed')
      window.scrollTo({ top: 0, behavior: 'smooth' })
    } catch (error) {
      setAlbumMessage(`Could not save this album: ${error instanceof Error ? error.message : 'Please try again.'}`)
    } finally {
      setSavingAlbum(false)
    }
  }

  const addFiles = async (files: File[]) => {
    const accepted = files.filter((file) => file.type.startsWith('video/'))
    const remaining = Math.max(0, 6 - clips.length)
    const videos = accepted.slice(0, remaining)
    if (!videos.length) {
      setAlbumMessage(accepted.length ? 'This demo supports up to six videos per album.' : 'Choose a video file to create an album.')
      return
    }
    if (accepted.length > videos.length) {
      setAlbumMessage(`Only ${videos.length} videos fit in this album; the rest were not added.`)
    }
    if (firebaseConfigured && !user) {
      setAlbumMessage('Sign in before uploading videos to your account.')
      return
    }
    const hasTripDates = tripStartDate || tripEndDate
    if (hasTripDates && (!tripStartDate || !tripEndDate || tripEndDate <= tripStartDate)) {
      setAlbumMessage('Enter both trip dates and choose a trip end date after the start date.')
      return
    }
    const tooLarge = videos.find((file) => file.size > 100 * 1024 * 1024)
    if (tooLarge) {
      setAlbumMessage(`${tooLarge.name} is larger than the 100 MB per-video limit.`)
      return
    }
    const additions = videos.map((file) => ({
      id: crypto.randomUUID(),
      file,
      url: URL.createObjectURL(file),
      status: 'analyzing' as const,
      travelStatus: 'analyzing' as const,
    }))
    setDraftAlbum(null)
    setClips((current) => [...current, ...additions])
    setStudioOpen(true)

    const metadataResults = await Promise.all(additions.map(async (clip) => {
      try {
        return { id: clip.id, file: clip.file, metadata: await travelMetadataFromVideo(clip.file) }
      } catch {
        return { id: clip.id, file: clip.file, metadata: null, failed: true }
      }
    }))

    setClips((current) => current.map((clip) => {
      const result = metadataResults.find((item) => item.id === clip.id)
      if (!result) return clip
      const travelStatus: Clip['travelStatus'] = 'failed' in result ? 'error' : result.metadata ? 'found' : 'missing'
      return {
        ...clip,
        travelStatus,
        travel: result.metadata ?? undefined,
      }
    }))

    const hasLocation = metadataResults.some((result) => result.metadata)
    if (metadataResults.some((result) => 'failed' in result)) {
      setTravelMessage('Some video metadata could not be read. Those files were not added to the travel archive.')
    } else if (!hasLocation) {
      setTravelMessage('No embedded GPS location was found in these videos.')
    }

    let nextTheme = theme
    try {
      nextTheme = await themeFromVideo(videos[0])
      setTheme(nextTheme)
      setClips((current) => current.map((clip) => additions.some((item) => item.id === clip.id) ? { ...clip, status: 'ready' } : clip))
    } catch {
      setClips((current) => current.map((clip) => additions.some((item) => item.id === clip.id) ? { ...clip, status: 'error' } : clip))
    }

    const analyzedAdditions = additions.map((clip) => {
      const result = metadataResults.find((item) => item.id === clip.id)
      return {
        ...clip,
        status: 'ready' as const,
        travelStatus: !result ? 'error' as const : 'failed' in result ? 'error' as const : result.metadata ? 'found' as const : 'missing' as const,
        travel: result?.metadata ?? undefined,
      }
    })
    const allClips = [...clips, ...analyzedAdditions]
    const regions = [...new Set(allClips.flatMap((clip) => clip.travel ? [clip.travel.region] : []))]
    const primaryLocation = allClips.find((clip) => clip.travel)?.travel
    const album: Album = {
      id: crypto.randomUUID(),
      title: albumTitle.trim() || videos[0].name.replace(/\.[^/.]+$/, ''),
      ...(tripDestination.trim() ? { destination: tripDestination.trim() } : {}),
      ...(tripDescription.trim() ? { tripDescription: tripDescription.trim() } : {}),
      ...(tripStartDate ? { tripStartDate, tripEndDate } : {}),
      createdAt: new Date().toISOString(),
      clipCount: allClips.length,
      regions,
      primary: nextTheme.primary,
      secondary: nextTheme.secondary,
      ...(primaryLocation ? {
        searchLocation: {
          latitude: Math.round(primaryLocation.latitude * 100) / 100,
          longitude: Math.round(primaryLocation.longitude * 100) / 100,
        },
      } : {}),
    }
    setDraftAlbum(album)
    setAlbumMessage('Videos are ready. Save the album to add it and its videos to your feed.')
  }

  const onFiles = (event: ChangeEvent<HTMLInputElement>) => {
    void addFiles(Array.from(event.target.files ?? []))
    event.target.value = ''
  }

  const onDrop = (event: DragEvent) => {
    event.preventDefault(); setDragging(false)
    void addFiles(Array.from(event.dataTransfer.files))
  }

  const removeClip = (id: string) => {
    const remaining = clips.filter((clip) => clip.id !== id)
    setClips((current) => {
      const match = current.find((clip) => clip.id === id)
      if (match) URL.revokeObjectURL(match.url)
      return current.filter((clip) => clip.id !== id)
    })
    setDraftAlbum((current) => {
      if (!current) return null
      const updated: Album = {
        ...current,
        clipCount: remaining.length,
        regions: [...new Set(remaining.flatMap((clip) => clip.travel ? [clip.travel.region] : []))],
      }
      const location = remaining.find((clip) => clip.travel)?.travel
      if (location) {
        updated.searchLocation = {
          latitude: Math.round(location.latitude * 100) / 100,
          longitude: Math.round(location.longitude * 100) / 100,
        }
      } else {
        delete updated.searchLocation
      }
      return remaining.length ? updated : null
    })
  }

  const style = {
    '--primary': theme.primary,
    '--secondary': theme.secondary,
    '--paper': theme.background,
    '--ink': theme.ink,
    '--energy': `${theme.energy / 100}`,
  } as CSSProperties
  const selectedTripOffers = travelOffers.filter((offer) => selectedOfferIds.includes(offer.id))
  const selectedTripCurrencies = new Set(selectedTripOffers.map((offer) => offer.currency))
  const selectedTripTotal = selectedTripOffers.reduce((total, offer) => total + (offer.price ?? 0), 0)
  const canShowTripTotal = selectedTripOffers.length > 0
    && selectedTripOffers.every((offer) => offer.price !== null && Boolean(offer.currency))
    && selectedTripCurrencies.size === 1

  if (firebaseConfigured && authLoading) {
    return <main className="auth-main" style={style}><div className="auth-card"><span className="step">ROAM / MAKE</span><h1>Opening your space.</h1><p>Checking your account…</p></div></main>
  }

  if (firebaseConfigured && !user) {
    return (
      <main className="auth-main" style={style}>
        <div className="auth-card">
          <button className="brand" onClick={() => setScreen('landing')} aria-label="Roam Make home"><span>ROAM</span><i>/</i><span>MAKE</span></button>
          <span className="step">{authMode === 'signup' ? 'START YOUR ACCOUNT' : 'YOUR JOURNEY, REMEMBERED'}</span>
          <h1>{authMode === 'signup' ? 'Create your account.' : 'Welcome back.'}</h1>
          <p>Sign in to save travel albums, securely store your videos, and keep your journeys with you.</p>
          <button className="google-signin" onClick={() => void signInWithGoogle()}>Continue with Google</button>
          <div className="auth-divider">OR CONTINUE WITH EMAIL</div>
          <form className="auth-form" onSubmit={(event) => void submitAuth(event)}>
            <label htmlFor="authEmail">Email address</label>
            <input id="authEmail" type="email" autoComplete="email" required value={authEmail} onChange={(event) => setAuthEmail(event.target.value)}/>
            <label htmlFor="authPassword">Password</label>
            <input id="authPassword" type="password" autoComplete={authMode === 'signup' ? 'new-password' : 'current-password'} minLength={8} required value={authPassword} onChange={(event) => setAuthPassword(event.target.value)}/>
            <button className="primary" type="submit">{authMode === 'signup' ? 'Create account' : 'Sign in'}</button>
          </form>
          {authMessage && <p className="auth-message" role="alert">{authMessage}</p>}
          <p className="auth-switch">
            {authMode === 'signin' ? 'New to Roam / Make?' : 'Already have an account?'}{' '}
            <button onClick={() => { setAuthMode(authMode === 'signin' ? 'signup' : 'signin'); setAuthMessage('') }}>
              {authMode === 'signin' ? 'Create an account' : 'Sign in'}
            </button>
          </p>
        </div>
      </main>
    )
  }

  return (
    <main style={style}>
      <nav className="nav">
        <button className="brand" onClick={() => setScreen('landing')} aria-label="Roam Make home"><span>ROAM</span><i>/</i><span>MAKE</span></button>
        <div className="nav-links">
          {screen === 'landing' ? <>
            <a href="#how">How it works</a>
            <button onClick={() => openFeed('discover')}>Open feed <ArrowUpRight size={16}/></button>
          </> : screen === 'profile' ? <>
            <button onClick={() => openFeed('discover')}><Compass size={15}/> Discover</button>
            <button className="selected" onClick={closeProfile}><UserRound size={15}/> Profile</button>
          </> : <>
            <button className={feedCategory === 'discover' ? 'selected' : ''} onClick={() => openFeed('discover')}><Compass size={15}/> Discover</button>
            <button className={feedCategory === 'create' ? 'selected' : ''} onClick={() => openFeed('create')}><Plus size={15}/> Create</button>
            <button className={feedCategory === 'friends' ? 'selected' : ''} onClick={() => openFeed('friends')}><Users size={15}/> Friends</button>
          </>}
        </div>
        <button className={`profile-nav${screen === 'profile' ? ' selected' : ''}`} onClick={openProfile} aria-label="View profile"><UserRound size={16}/><span>Profile</span></button>
        {user && <button className="sign-out" onClick={() => void signOutCurrentUser()} aria-label={`Sign out ${user.email ?? 'account'}`}>Sign out</button>}
        <button className="menu" aria-label="Open feed" onClick={() => openFeed('discover')}><Menu /></button>
      </nav>

      <input ref={inputRef} onChange={onFiles} type="file" accept="video/*" multiple hidden />

      {screen === 'landing' ? <>
      <section className="hero shell" id="top">
        <div className="eyebrow"><span className="live-dot"/> A living canvas for your next chapter</div>
        <h1>Your story<br/>already has a <em>colour.</em></h1>
        <p className="lede">Upload the moments that move you. We’ll shape a digital home around their colour, rhythm, and energy.</p>
        <div className="hero-actions">
          <button className="primary" onClick={() => openFeed('discover')}>Open my feed <ArrowUpRight size={18}/></button>
          <button className="secondary-action" onClick={() => openFeed('create')}>Create an album <Plus size={16}/></button>
          <a href="#how">See how it moves <ArrowDown size={17}/></a>
        </div>
        <div className="orbit orbit-a"/><div className="orbit orbit-b"/>
        <div className="postcard card-one"><span>CHASE THE FEELING</span></div>
        <div className="postcard card-two"><Globe2/><span>43.65° N<br/>79.38° W</span></div>
        <div className="scribble">build from<br/><strong>what’s real ↗</strong></div>
      </section>

      <section className="studio-wrap" id="how">
        <div className={`dropzone shell ${dragging ? 'dragging' : ''}`} onDragOver={(e) => { e.preventDefault(); setDragging(true) }} onDragLeave={() => setDragging(false)} onDrop={onDrop}>
          <div className="drop-copy">
            <span className="step">01 — THE RAW MATERIAL</span>
            <h2>Drop in your world.</h2>
            <p>Choose up to six short videos. Location metadata is read on this device; exact coordinates are never saved.</p>
          </div>
          <button className="upload-card" onClick={() => inputRef.current?.click()}>
            <span className="upload-icon"><Plus /></span>
            <strong>{clips.length ? 'Add another moment' : 'Choose your videos'}</strong>
            <small>MP4, MOV or WebM · up to 6 clips</small>
          </button>
        </div>

        {studioOpen && (
          <div className="studio shell" aria-live="polite">
            <div className="studio-head"><div><span className="step">YOUR SIGNAL</span><h3>{clips.length ? 'A world is taking shape.' : 'Your studio is ready.'}</h3></div><button onClick={() => setStudioOpen(false)} aria-label="Close studio"><X/></button></div>
            {clips.length ? (
              <div className="clip-grid">
                {clips.map((clip, index) => <article className="clip" key={clip.id}>
                  <video src={clip.url} muted loop autoPlay={playing} playsInline />
                  <div className="clip-shade"/>
                  <span className="clip-number">0{index + 1}</span>
                  <button onClick={() => removeClip(clip.id)} disabled={savingAlbum} aria-label={`Remove ${clip.file.name}`}><X size={15}/></button>
                  <div className="clip-meta">
                    <strong>{clip.file.name.replace(/\.[^/.]+$/, '')}</strong>
                    <small>{clip.status === 'analyzing' ? 'Reading colour…' : clip.status === 'ready' ? 'Palette captured' : 'Preview only'}</small>
                    <small>{clip.travelStatus === 'analyzing' ? 'Checking travel metadata…' : clip.travelStatus === 'found' ? clip.travel?.region : clip.travelStatus === 'missing' ? 'No embedded GPS' : 'Metadata could not be read'}</small>
                  </div>
                </article>)}
                {clips.length < 6 && <button className="clip add-clip" onClick={() => inputRef.current?.click()}><Plus/><span>Add a moment</span></button>}
              </div>
            ) : <button className="empty-studio" onClick={() => inputRef.current?.click()}><Film/><span>Select a few video moments to begin</span></button>}
            {clips.length > 0 && (
              <>
                {firebaseConfigured && !mediaStorageConfigured && <p className="create-note">No-billing test mode: account sign-in and travel metadata are available, but video collections cannot be saved or shared without Firebase Storage. Billing is not enabled.</p>}
                {firebaseConfigured && mediaStorageConfigured && (
                  <label className="publish-consent">
                    <input type="checkbox" checked={publishConfirmed} onChange={(event) => setPublishConfirmed(event.target.checked)} disabled={savingAlbum}/>
                    <span>I understand this collection, its videos, destination, dates, and description will be visible to all signed-in app users.</span>
                  </label>
                )}
                <div className="draft-save-row">
                  <span>{draftAlbum ? 'Your videos are staged and ready to save.' : 'Analyzing your videos…'}</span>
                  <button className="primary" onClick={() => void saveDraftAlbum()} disabled={!draftAlbum || savingAlbum || (firebaseConfigured && (!mediaStorageConfigured || !publishConfirmed)) || clips.some((clip) => clip.status === 'analyzing' || clip.travelStatus === 'analyzing')}>
                    {savingAlbum ? 'Publishing videos…' : firebaseConfigured ? mediaStorageConfigured ? 'Publish collection' : 'Unavailable without Storage' : 'Save collection'}
                  </button>
                </div>
              </>
            )}
            <section className="travel-archive" aria-labelledby="travelTitle">
              <div className="archive-heading"><div><span className="step">YOUR TRAVEL MEMORY</span><h3 id="travelTitle">Places in your videos</h3></div><Globe2 size={20}/></div>
              {firebaseConfigured ? (
                <p className="archive-note">Approximate travel metadata is saved privately to your signed-in account. Exact GPS coordinates are not stored.</p>
              ) : (
                <>
                  <label className="account-field" htmlFor="accountEmail">Local account email</label>
                  <input
                    id="accountEmail"
                    className="account-input"
                    type="email"
                    autoComplete="email"
                    placeholder="you@example.com"
                    value={accountEmail}
                    onChange={(event) => setAccountEmail(event.target.value)}
                  />
                  <p className="archive-note">Entries are saved on this device under this email. This local demo does not provide account sync or secure authentication.</p>
                </>
              )}
              {travelMessage && <p className="travel-message" role="status">{travelMessage}</p>}
              {travelRecords.length > 0 && (
                <ul className="travel-list">
                  {travelRecords.map((record) => (
                    <li key={record.id}>
                      <span className="travel-pin"><Globe2 size={16}/></span>
                      <span className="travel-details">
                        <strong>{record.region}</strong>
                        <small>{record.timezone}{record.capturedAt ? ` · ${record.capturedAt.slice(0, 10)}` : ''}</small>
                      </span>
                    </li>
                  ))}
                </ul>
              )}
            </section>
            <div className="signal-bar">
              <div><Sparkles size={18}/><span>ENERGY</span><strong>{theme.energy}%</strong></div>
              <div className="meter"><i style={{ width: `${theme.energy}%` }}/></div>
              <div className="swatches"><i style={{background: theme.primary}}/><i style={{background: theme.secondary}}/><i style={{background: theme.ink}}/></div>
              <button className="play" onClick={() => setPlaying(!playing)}>{playing ? <Pause size={17}/> : <Play size={17}/>} {playing ? 'Pause' : 'Play'}</button>
            </div>
          </div>
        )}
      </section>

      <section className="process shell">
        <div className="process-intro"><span className="step">02 — YOUR DIGITAL HOME</span><h2>Not a template.<br/><em>A translation.</em></h2></div>
        <div className="process-list">
          <article><span>01</span><div><h3>We read the atmosphere</h3><p>Colour, contrast, and visual intensity become the foundation of your space.</p></div><Check/></article>
          <article><span>02</span><div><h3>You shape the story</h3><p>Reorder moments, tune the mood, and add the words that make it yours.</p></div><Check/></article>
          <article><span>03</span><div><h3>Take it everywhere</h3><p>A responsive React foundation designed to travel from web toward native apps.</p></div><ArrowUpRight/></article>
        </div>
      </section>

      <section className="manifesto" id="stories"><div className="shell"><p>FOR THE ONES BUILDING<br/>BETWEEN <em>PLACES.</em></p><span>Founders · creators · wanderers · people in motion</span></div></section>
      </> : screen === 'profile' ? (
        <ProfilePage
          user={user}
          localEmail={accountEmail}
          albumCount={albums.length}
          videoCount={albums.reduce((total, album) => total + album.clipCount, 0)}
          placeCount={travelRecords.length}
          onBack={closeProfile}
          onSignOut={() => void signOutCurrentUser()}
          onConnectPayouts={() => void connectCreatorPayouts()}
          payoutMessage={payoutMessage}
        />
      ) : (
        <section className="feed-page shell">
          <div className="feed-topline">
            <button className="back-link" onClick={() => setScreen('landing')}><ArrowLeft size={16}/> Back to Roam / Make</button>
            <span className="local-pill"><span/> {firebaseConfigured ? 'PRIVATE ACCOUNT' : 'LOCAL DEMO'}</span>
          </div>
          {selectedAlbum ? (
            <div className="album-detail">
              <button className="back-link" onClick={() => setSelectedAlbum(null)}><ArrowLeft size={16}/> All albums</button>
              <div className="album-detail-cover" style={{ '--album-primary': selectedAlbum.primary, '--album-secondary': selectedAlbum.secondary } as CSSProperties}>
                <span className="album-index">ROAM / MAKE · ALBUM</span>
                <h1>{selectedAlbum.title}</h1>
                <span>{selectedAlbum.destination || selectedAlbum.regions.join(' · ') || 'Location not detected'}</span>
              </div>
              <div className="album-detail-meta"><span>{selectedAlbum.clipCount} video {selectedAlbum.clipCount === 1 ? 'moment' : 'moments'}</span><span>{new Date(selectedAlbum.createdAt).toLocaleDateString()}</span></div>
              {(selectedAlbum.destination || selectedAlbum.tripDescription || selectedAlbum.tripStartDate) && (
                <section className="trip-story" aria-label="Trip details">
                  <span className="step">THE TRIP</span>
                  {selectedAlbum.destination && <h2>{selectedAlbum.destination}</h2>}
                  {selectedAlbum.tripStartDate && selectedAlbum.tripEndDate && (
                    <p className="trip-story-dates">{new Date(`${selectedAlbum.tripStartDate}T00:00:00`).toLocaleDateString()} — {new Date(`${selectedAlbum.tripEndDate}T00:00:00`).toLocaleDateString()}</p>
                  )}
                  {selectedAlbum.tripDescription && <p className="trip-story-description">{selectedAlbum.tripDescription}</p>}
                </section>
              )}
              {selectedAlbum.searchLocation && (
                <div className="travel-search-panel">
                  <div className="travel-search-heading"><span className="step">A JOURNEY NEAR</span><strong>{selectedAlbum.regions.join(' · ') || 'A detected location'}</strong><small>Search sends an approximate location to the travel backend only when you request it. Exact GPS is not stored.</small></div>
                  <div className="travel-dates">
                    <label>Check in<input type="date" value={checkIn} onChange={(event) => setCheckIn(event.target.value)}/></label>
                    <label>Check out<input type="date" value={checkOut} onChange={(event) => setCheckOut(event.target.value)}/></label>
                    <button className="primary" onClick={() => void searchForTravel(selectedAlbum)} disabled={searchingOffers}>
                      <MapPin size={16}/>{searchingOffers ? 'Searching…' : 'Find stays & activities'}
                    </button>
                  </div>
                </div>
              )}
              {offerMessage && <p className="feed-status" role="status">{offerMessage}</p>}
              {travelOffers.length > 0 && (
                <>
                  <div className="offer-grid">
                    {travelOffers.map((offer) => {
                      const selected = selectedOfferIds.includes(offer.id)
                      const canSelect = offer.price !== null && Boolean(offer.currency)
                      return (
                        <article className={`offer-card${selected ? ' selected' : ''}`} key={offer.id}>
                          <span className="step">{offer.category === 'stay' ? 'STAY' : 'ACTIVITY'} · {offer.provider}</span>
                          <strong>{offer.name}</strong>
                          <small>{offer.location}</small>
                          {offer.price !== null && <span className="offer-price">{offer.currency ?? ''} {offer.price.toLocaleString()}</span>}
                          <a className="offer-link" href={offer.url} target="_blank" rel="noreferrer">View details <ArrowUpRight size={14}/></a>
                          <button
                            className="offer-select"
                            disabled={!canSelect}
                            aria-pressed={selected}
                            onClick={() => setSelectedOfferIds((current) => selected ? current.filter((id) => id !== offer.id) : [...current, offer.id])}
                          >
                            {selected ? 'Remove from trip' : canSelect ? 'Add to trip' : 'Price unavailable'}
                          </button>
                        </article>
                      )
                    })}
                  </div>
                  {selectedOfferIds.length > 0 && (
                    <section className="itinerary-summary">
                      <div>
                        <span className="step">YOUR TRIP PLAN</span>
                        <strong>{selectedTripOffers.length} selected {selectedTripOffers.length === 1 ? 'item' : 'items'}{canShowTripTotal ? ` · Est. ${[...selectedTripCurrencies][0]} ${selectedTripTotal.toLocaleString()}` : ''}</strong>
                        <small>Final availability and pricing are verified securely before payment.</small>
                      </div>
                      <button className="primary" onClick={() => void startCheckout()} disabled={checkoutLoading}>
                        {checkoutLoading ? 'Preparing secure checkout…' : 'Continue to secure checkout'}
                      </button>
                    </section>
                  )}
                  {checkoutMessage && <p className="feed-status" role="status">{checkoutMessage}</p>}
                  {!import.meta.env.VITE_TRIP_CHECKOUT_URL && <p className="feed-disclaimer"><LockKeyhole size={14}/> Secure checkout is not active until the Stripe Connect backend is configured. No payment has been taken.</p>}
                </>
              )}
              {albumMedia.length > 0 ? (
                <div className="album-media-grid">
                  {albumMedia.filter((media) => media.contentType.startsWith('video/')).map((media) => <video key={media.path} src={media.url} controls playsInline aria-label={media.name}/>)}
                </div>
              ) : albumMediaLoading ? <p className="feed-disclaimer">Loading your saved videos…</p>
                : <p className="feed-disclaimer">{selectedAlbum.media?.length ? 'Saved videos are currently unavailable.' : 'No saved video files are attached to this album.'}</p>}
            </div>
          ) : feedCategory === 'discover' ? (
            <>
              <FeedTabs active={feedCategory} onSelect={openFeed}/>
              <header className="feed-heading">
                <span className="step">THE TRAVEL ALBUM FEED</span>
                <h1>Discover<br/><em>somewhere.</em></h1>
                <p>Journeys made from the moments people choose to keep.</p>
              </header>
              {albumMessage && <p className="feed-status" role="status">{albumMessage}</p>}
              <div className="feed-toolbar">
                <div><strong>{albums.length}</strong><span>{albums.length === 1 ? 'album' : 'albums'} {firebaseConfigured ? 'in your account' : 'on this device'}</span></div>
                <button className="primary" onClick={() => openFeed('create')}><Plus size={17}/> Create an album</button>
              </div>
              <p className="feed-disclaimer"><LockKeyhole size={14}/>{firebaseConfigured ? mediaStorageConfigured ? 'Published videos and trip details are visible to all signed-in users. Account email and private records are not published.' : 'No-billing Firebase test: sign-in and travel metadata use your account, but video collections cannot be published without Firebase Storage.' : 'Local demo: collections are private to this browser. Configure Firebase to publish across signed-in users.'}</p>
              {accountDataLoading ? (
                <div className="feed-empty" role="status">
                  <span className="empty-orbit"><Globe2 size={27}/></span>
                  <h2>Restoring your journeys.</h2>
                  <p>Loading your saved albums and videos…</p>
                </div>
              ) : albums.length ? (
                <div className="album-grid">
                  {albums.map((album, index) => (
                    <AlbumFeedCard album={album} index={index} user={user} onOpen={() => openAlbum(album)} key={album.id}/>
                  ))}
                </div>
              ) : (
                <div className="feed-empty">
                  <span className="empty-orbit"><Globe2 size={27}/></span>
                  <h2>Your video feed starts here.</h2>
                  <p>Save a video album and its clips will play here.</p>
                  <button className="primary" onClick={() => openFeed('create')}><Plus size={17}/> Add videos to your feed</button>
                </div>
              )}
            </>
          ) : feedCategory === 'create' ? (
            <>
              <FeedTabs active={feedCategory} onSelect={openFeed}/>
              <header className="feed-heading">
                <span className="step">MAKE A NEW ALBUM</span>
                <h1>Build a story<br/><em>from motion.</em></h1>
                <p>Add the videos from one trip or idea. We’ll collect them into an album for your feed.</p>
              </header>
              <section className={`create-panel ${dragging ? 'dragging' : ''}`} onDragOver={(event) => { event.preventDefault(); setDragging(true) }} onDragLeave={() => setDragging(false)} onDrop={onDrop}>
                {!firebaseConfigured && (
                  <>
                    <label className="create-label" htmlFor="feedAccountEmail">Local account email</label>
                    <input id="feedAccountEmail" className="create-input account-email-input" type="email" autoComplete="email" placeholder="you@example.com" value={accountEmail} onChange={(event) => setAccountEmail(event.target.value)}/>
                    <p className="create-note">Used only to organize saved albums on this device. This is not secure account authentication.</p>
                  </>
                )}
                {firebaseConfigured && mediaStorageConfigured && <p className="create-note">Saving publishes the collection and its videos to all signed-in Roam / Make users.</p>}
                {firebaseConfigured && !mediaStorageConfigured && <p className="create-note">No-billing test mode: account sign-in and travel metadata are available, but video collections cannot be saved or shared without Firebase Storage. Billing is not enabled.</p>}
                {!firebaseConfigured && <p className="create-note">Local demo collections are saved on this device and are not public to other users.</p>}
                <label className="create-label" htmlFor="albumTitle">Album title</label>
                <input id="albumTitle" className="create-input" value={albumTitle} onChange={(event) => setAlbumTitle(event.target.value)} placeholder="Give this journey a name" maxLength={80}/>
                <span className="create-label">Trip details <span className="optional-label">OPTIONAL</span></span>
                <label className="sr-only" htmlFor="tripDestination">Destination</label>
                <input id="tripDestination" className="create-input" value={tripDestination} onChange={(event) => setTripDestination(event.target.value)} placeholder="Destination or region" maxLength={120}/>
                <div className="trip-date-fields">
                  <label className="create-label" htmlFor="tripStartDate">Trip starts<input id="tripStartDate" className="create-input" type="date" value={tripStartDate} onChange={(event) => setTripStartDate(event.target.value)}/></label>
                  <label className="create-label" htmlFor="tripEndDate">Trip ends<input id="tripEndDate" className="create-input" type="date" value={tripEndDate} onChange={(event) => setTripEndDate(event.target.value)} min={tripStartDate || undefined}/></label>
                </div>
                <label className="sr-only" htmlFor="tripDescription">Trip description</label>
                <textarea id="tripDescription" className="create-input create-textarea" value={tripDescription} onChange={(event) => setTripDescription(event.target.value)} placeholder="Write a short description of this trip for the feed…" maxLength={600} rows={4}/>
                <p className="create-note">These details will appear with your album in the feed.</p>
                <button className="create-upload" onClick={() => inputRef.current?.click()}><span className="upload-icon"><Plus/></span><strong>Choose travel videos</strong><small>MP4, MOV, or WebM · up to six videos per album</small></button>
                <p className="upload-privacy"><LockKeyhole size={14}/>{firebaseConfigured ? mediaStorageConfigured ? 'Videos are published for signed-in app users. Location metadata is processed on-device; only a coarse search location is published.' : 'Video selection and on-device metadata analysis are available, but this Firebase project has no video storage.' : 'Videos stay on this device in the demo. Location metadata is processed on-device.'}</p>
                <p className="upload-privacy">{firebaseConfigured ? mediaStorageConfigured ? 'Publish uploads the videos and makes this travel collection discoverable throughout the app.' : 'No video files or albums will be uploaded or saved to your cloud feed.' : 'Save stores this device’s video files in IndexedDB and the album details in the local Discover feed.'}</p>
                {albumMessage && <p className="feed-disclaimer" role="status">{albumMessage}</p>}
              </section>
              {studioOpen && clips.length > 0 && (
                <section className="studio create-studio" aria-live="polite">
                  <div className="studio-head"><div><span className="step">YOUR UPLOADS</span><h3>Moments in this session</h3></div></div>
                  <div className="clip-grid">
                    {clips.map((clip, index) => <article className="clip" key={clip.id}>
                      <video src={clip.url} muted loop autoPlay={playing} playsInline/>
                      <div className="clip-shade"/>
                      <span className="clip-number">0{index + 1}</span>
                      <div className="clip-meta"><strong>{clip.file.name.replace(/\.[^/.]+$/, '')}</strong><small>{clip.travelStatus === 'found' ? clip.travel?.region : clip.travelStatus === 'analyzing' ? 'Reading travel metadata…' : 'Location not detected'}</small></div>
                    </article>)}
                  </div>
                  {firebaseConfigured && mediaStorageConfigured && (
                    <label className="publish-consent">
                      <input type="checkbox" checked={publishConfirmed} onChange={(event) => setPublishConfirmed(event.target.checked)} disabled={savingAlbum}/>
                      <span>I understand this collection, its videos, destination, dates, and description will be visible to all signed-in app users.</span>
                    </label>
                  )}
                  <div className="draft-save-row">
                    <span>{draftAlbum ? `${clips.length} ${clips.length === 1 ? 'video' : 'videos'} ready to save.` : 'Analyzing your videos…'}</span>
                    <button className="primary" onClick={() => void saveDraftAlbum()} disabled={!draftAlbum || savingAlbum || (firebaseConfigured && (!mediaStorageConfigured || !publishConfirmed)) || clips.some((clip) => clip.status === 'analyzing' || clip.travelStatus === 'analyzing')}>
                      {savingAlbum ? 'Publishing videos…' : firebaseConfigured ? mediaStorageConfigured ? 'Publish collection' : 'Unavailable without Storage' : 'Save collection'}
                    </button>
                  </div>
                </section>
              )}
            </>
          ) : (
            <>
              <FeedTabs active={feedCategory} onSelect={openFeed}/>
              <div className="friends-empty">
                <span className="friends-icon"><Users size={25}/></span>
                <span className="step">YOUR PEOPLE, YOUR PLACES</span>
                <h1>Travel is better<br/><em>shared.</em></h1>
                <p>Friends albums and shared journeys will appear here when account connections and the Roam / Make backend are ready.</p>
                <button className="primary" onClick={() => openFeed('discover')}><Compass size={17}/> Explore your albums</button>
              </div>
            </>
          )}
        </section>
      )}
      <footer className="shell"><button className="brand" onClick={() => { setScreen('landing'); window.scrollTo({ top: 0, behavior: 'smooth' }) }}><span>ROAM</span><i>/</i><span>MAKE</span></button><p>Make something that feels like where you’re going.</p><span>© {new Date().getFullYear()}</span></footer>
    </main>
  )
}

function FeedTabs({ active, onSelect }: { active: FeedCategory; onSelect: (category: FeedCategory) => void }) {
  return (
    <nav className="feed-tabs" aria-label="Feed categories">
      <button className={active === 'discover' ? 'active' : ''} aria-current={active === 'discover' ? 'page' : undefined} onClick={() => onSelect('discover')}><Compass size={16}/> Discover</button>
      <button className={active === 'create' ? 'active' : ''} aria-current={active === 'create' ? 'page' : undefined} onClick={() => onSelect('create')}><Plus size={16}/> Create</button>
      <button className={active === 'friends' ? 'active' : ''} aria-current={active === 'friends' ? 'page' : undefined} onClick={() => onSelect('friends')}><Users size={16}/> Friends</button>
    </nav>
  )
}

function ProfilePage({ user, localEmail, albumCount, videoCount, placeCount, onBack, onSignOut, onConnectPayouts, payoutMessage }: {
  user: User | null
  localEmail: string
  albumCount: number
  videoCount: number
  placeCount: number
  onBack: () => void
  onSignOut: () => void
  onConnectPayouts: () => void
  payoutMessage: string
}) {
  const displayName = user?.displayName?.trim() || (user?.email ? user.email.split('@')[0] : 'Local profile')
  const initials = displayName.split(/\s+/).map((part) => part[0]).slice(0, 2).join('').toUpperCase()
  const providerNames = user?.providerData.map((provider) => {
    if (provider.providerId === 'google.com') return 'Google'
    if (provider.providerId === 'password') return 'Email and password'
    return provider.providerId
  }).filter(Boolean)
  const joinedDate = user?.metadata.creationTime
    ? new Date(user.metadata.creationTime).toLocaleDateString(undefined, { year: 'numeric', month: 'long', day: 'numeric' })
    : null
  const lastSignIn = user?.metadata.lastSignInTime
    ? new Date(user.metadata.lastSignInTime).toLocaleDateString(undefined, { year: 'numeric', month: 'long', day: 'numeric' })
    : null

  return (
    <section className="profile-page shell">
      <div className="profile-topline">
        <button className="back-link" onClick={onBack}><ArrowLeft size={16}/> Back</button>
        <span className="step">YOUR ACCOUNT</span>
      </div>
      <header className="profile-header">
        <div className="profile-avatar">
          {user?.photoURL ? <img src={user.photoURL} alt=""/> : <span>{initials || 'RM'}</span>}
        </div>
        <div className="profile-heading-copy">
          <span className="step">{user ? 'ROAM / MAKE MEMBER' : 'LOCAL DEMO PROFILE'}</span>
          <h1>{displayName}</h1>
          <p>{user?.email || localEmail || 'No email added to this local profile'}</p>
        </div>
        {user && <button className="profile-sign-out" onClick={onSignOut}>Sign out</button>}
      </header>

      <section className="profile-section">
        <div className="profile-section-heading"><span className="step">ACCOUNT INFORMATION</span><h2>Your details</h2></div>
        <div className="profile-details">
          <article className="profile-detail">
            <span className="profile-detail-icon"><UserRound size={17}/></span>
            <div><small>Display name</small><strong>{user?.displayName || 'Not set'}</strong></div>
          </article>
          <article className="profile-detail">
            <span className="profile-detail-icon"><Mail size={17}/></span>
            <div><small>Email address</small><strong>{user?.email || localEmail || 'Not provided'}</strong></div>
          </article>
          {user && (
            <>
              <article className="profile-detail">
                <span className="profile-detail-icon"><LockKeyhole size={17}/></span>
                <div><small>Sign-in method</small><strong>{providerNames?.join(' · ') || 'Firebase account'}</strong></div>
              </article>
              <article className="profile-detail">
                <span className="profile-detail-icon"><CalendarDays size={17}/></span>
                <div><small>Member since</small><strong>{joinedDate || 'Not available'}</strong></div>
              </article>
              <article className="profile-detail">
                <span className="profile-detail-icon"><CalendarDays size={17}/></span>
                <div><small>Last sign in</small><strong>{lastSignIn || 'Not available'}</strong></div>
              </article>
              <article className="profile-detail profile-uid">
                <span className="profile-detail-icon"><Globe2 size={17}/></span>
                <div><small>Account ID</small><strong>{user.uid}</strong></div>
              </article>
            </>
          )}
          {!user && (
            <article className="profile-detail">
              <span className="profile-detail-icon"><LockKeyhole size={17}/></span>
              <div><small>Account type</small><strong>Local device profile</strong></div>
            </article>
          )}
        </div>
        {!user && <p className="profile-local-note">This profile is only a local organizer for this browser. Sign in with Firebase to use a secure account across devices.</p>}
      </section>

      <section className="profile-section profile-activity">
        <div className="profile-section-heading"><span className="step">YOUR ROAM / MAKE</span><h2>Saved here</h2></div>
        <div className="profile-stats">
          <article><strong>{albumCount}</strong><span>{albumCount === 1 ? 'album' : 'albums'}</span></article>
          <article><strong>{videoCount}</strong><span>{videoCount === 1 ? 'video' : 'videos'}</span></article>
          <article><strong>{placeCount}</strong><span>{placeCount === 1 ? 'place' : 'places'}</span></article>
        </div>
      </section>
      {user && (
        <section className="profile-section payout-section">
          <div className="profile-section-heading"><span className="step">CREATOR PAYOUTS</span><h2>Connect Stripe</h2></div>
          <div className="payout-card">
            <div><strong>Receive payments for trip plans</strong><p>Connect a Stripe account to receive creator payouts when travelers book selected itinerary items.</p></div>
            <button className="primary" onClick={onConnectPayouts}>Set up payouts <ArrowUpRight size={15}/></button>
          </div>
          {payoutMessage && <p className="feed-status" role="status">{payoutMessage}</p>}
          {!import.meta.env.VITE_STRIPE_CONNECT_URL && <p className="profile-local-note">Creator payouts are unavailable until the secure Stripe Connect onboarding backend is configured.</p>}
        </section>
      )}
    </section>
  )
}

function AlbumFeedCard({ album, index, user, onOpen }: {
  album: Album
  index: number
  user: User | null
  onOpen: () => void
}) {
  const postRef = useRef<HTMLElement>(null)
  const [previewMedia, setPreviewMedia] = useState<Array<{ name: string; contentType: string; path: string; url: string }>>([])
  const [loading, setLoading] = useState(false)
  const [previewError, setPreviewError] = useState(false)

  useEffect(() => {
    const mediaItems = album.media ?? []
    const post = postRef.current
    setPreviewMedia([])
    if (!mediaItems.length || !post) return
    let cancelled = false
    let objectUrls: string[] = []
    const loadPreview = async () => {
      setLoading(true)
      try {
        const media = user
          ? await loadAlbumMedia(user, mediaItems)
          : await loadLocalAlbumMedia(album.id)
        objectUrls = media.map((item) => item.url)
        if (cancelled) {
          objectUrls.forEach((url) => URL.revokeObjectURL(url))
          return
        }
        setPreviewMedia(media)
      } catch {
        if (!cancelled) setPreviewError(true)
      } finally {
        if (!cancelled) setLoading(false)
      }
    }
    const observer = new IntersectionObserver((entries) => {
      if (!entries.some((entry) => entry.isIntersecting)) return
      observer.disconnect()
      void loadPreview()
    }, { rootMargin: '160px' })
    observer.observe(post)
    return () => {
      cancelled = true
      observer.disconnect()
      objectUrls.forEach((url) => URL.revokeObjectURL(url))
    }
  }, [album.id, album.media, user])

  return (
    <article ref={postRef} className="video-feed-post">
      <div className="video-feed-post-heading">
        <div><span className="step">JOURNEY / {String(index + 1).padStart(2, '0')}</span><h2>{album.title}</h2><p>{album.destination || album.regions.join(' · ') || 'A journey in motion'}</p></div>
        <button className="video-feed-open" onClick={onOpen}>Trip details <ArrowUpRight size={15}/></button>
      </div>
      {previewMedia.length ? (
        <div className="video-feed-media">
          {previewMedia.filter((media) => media.contentType.startsWith('video/')).map((media) => (
            <video key={media.path} src={media.url} controls muted autoPlay loop playsInline preload="metadata" aria-label={media.name}/>
          ))}
        </div>
      ) : (
        <div className="video-feed-unavailable">
          {loading ? 'Loading saved videos…' : previewError ? 'Could not load the saved videos.' : 'No saved videos are attached to this album.'}
        </div>
      )}
      {album.tripDescription && <p className="video-feed-description">{album.tripDescription}</p>}
      <div className="video-feed-post-meta"><span>{album.clipCount} {album.clipCount === 1 ? 'video' : 'videos'}</span><span>{new Date(album.createdAt).toLocaleDateString()}</span></div>
    </article>
  )
}
