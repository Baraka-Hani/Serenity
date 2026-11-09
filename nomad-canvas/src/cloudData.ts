import type { User } from 'firebase/auth'
import type { DocumentData, QueryDocumentSnapshot } from 'firebase/firestore'
import {
  collection,
  deleteDoc,
  doc,
  getDocs,
  limit,
  orderBy,
  query,
  setDoc,
  startAfter,
  Timestamp,
  updateDoc,
} from 'firebase/firestore'
import { deleteObject, getBlob, ref, uploadBytes } from 'firebase/storage'
import type { StorageReference } from 'firebase/storage'
import type { Album, AlbumMedia, TravelRecord } from './models'
import { database, mediaStorage } from './firebase'

function toIsoDate(value: unknown): string {
  if (typeof value === 'string') return value
  if (value instanceof Timestamp) return value.toDate().toISOString()
  throw new Error('Cloud record is missing a valid timestamp.')
}

function requireDatabase() {
  if (!database) throw new Error('Cloud database is not configured.')
  return database
}

function requireMediaStorage() {
  if (!mediaStorage) throw new Error('Video publishing requires a configured Firebase Storage bucket.')
  return mediaStorage
}

export async function loadUserAlbums(user: User): Promise<Album[]> {
  const db = requireDatabase()
  const albumsCollection = collection(db, 'users', user.uid, 'albums')
  const albums: Album[] = []
  let lastDocument: QueryDocumentSnapshot<DocumentData> | undefined
  while (true) {
    const albumsQuery = lastDocument
      ? query(albumsCollection, orderBy('createdAt', 'desc'), startAfter(lastDocument), limit(50))
      : query(albumsCollection, orderBy('createdAt', 'desc'), limit(50))
    const snapshot = await getDocs(albumsQuery)
    albums.push(...snapshot.docs.map((albumDoc) => {
      const data = albumDoc.data()
      return { ...data, id: albumDoc.id, createdAt: toIsoDate(data.createdAt) } as Album
    }))
    if (snapshot.docs.length < 50) return albums
    lastDocument = snapshot.docs[snapshot.docs.length - 1]
  }
}

export async function loadPublishedTrips(): Promise<Album[]> {
  const db = requireDatabase()
  const publishedCollection = collection(db, 'publicTrips')
  const albums: Album[] = []
  let lastDocument: QueryDocumentSnapshot<DocumentData> | undefined
  while (true) {
    const publishedQuery = lastDocument
      ? query(publishedCollection, orderBy('createdAt', 'desc'), startAfter(lastDocument), limit(50))
      : query(publishedCollection, orderBy('createdAt', 'desc'), limit(50))
    const snapshot = await getDocs(publishedQuery)
    albums.push(...snapshot.docs.map((tripDoc) => {
      const data = tripDoc.data()
      if (typeof data.ownerId !== 'string') throw new Error(`Published trip ${tripDoc.id} is missing its owner.`)
      return { ...data, id: tripDoc.id, createdAt: toIsoDate(data.createdAt) } as Album
    }))
    if (snapshot.docs.length < 50) return albums
    lastDocument = snapshot.docs[snapshot.docs.length - 1]
  }
}

export async function createUserAlbum(user: User, album: Album, files: File[]): Promise<Album> {
  const db = requireDatabase()
  const storage = requireMediaStorage()
  const albumRef = doc(db, 'users', user.uid, 'albums', album.id)
  const publishedRef = doc(db, 'publicTrips', album.id)
  const media: AlbumMedia[] = []
  const uploadedRefs: StorageReference[] = []
  await setDoc(albumRef, {
    ...album,
    media: [],
  })

  try {
    for (const file of files) {
      const objectPath = `publicTrips/${user.uid}/${album.id}/${crypto.randomUUID()}`
      const objectRef = ref(storage, objectPath)
      await uploadBytes(objectRef, file, { contentType: file.type })
      uploadedRefs.push(objectRef)
      media.push({
        name: file.name,
        contentType: file.type,
        path: objectPath,
      })
    }

    await updateDoc(albumRef, { media })
    await setDoc(publishedRef, {
      ownerId: user.uid,
      title: album.title,
      ...(album.destination ? { destination: album.destination } : {}),
      ...(album.tripDescription ? { tripDescription: album.tripDescription } : {}),
      ...(album.tripStartDate ? { tripStartDate: album.tripStartDate } : {}),
      ...(album.tripEndDate ? { tripEndDate: album.tripEndDate } : {}),
      createdAt: album.createdAt,
      clipCount: album.clipCount,
      regions: album.regions,
      primary: album.primary,
      secondary: album.secondary,
      ...(album.searchLocation ? { searchLocation: album.searchLocation } : {}),
      media,
    })
    return { ...album, media }
  } catch (error) {
    const cleanup = await Promise.allSettled([
      ...uploadedRefs.map((objectRef) => deleteObject(objectRef)),
      deleteDoc(albumRef),
      deleteDoc(publishedRef),
    ])
    const cleanupFailed = cleanup.some((result) => result.status === 'rejected')
    throw new Error(`Album upload failed: ${error instanceof Error ? error.message : 'unknown upload error'}${cleanupFailed ? ' Some temporary cloud files may need cleanup.' : ''}`)
  }
}

export async function loadAlbumMedia(user: User, media: AlbumMedia[]): Promise<Array<AlbumMedia & { url: string }>> {
  const storage = requireMediaStorage()
  return Promise.all(media.map(async (item) => {
    const isPublishedMedia = /^publicTrips\/[^/]+\/[^/]+\/[^/]+$/.test(item.path)
    const isPrivateOwnerMedia = item.path.startsWith(`users/${user.uid}/albums/`)
    if (!isPublishedMedia && !isPrivateOwnerMedia) {
      throw new Error('Album media path is not published or privately owned by the signed-in account.')
    }
    return {
      ...item,
      url: URL.createObjectURL(await getBlob(ref(storage, item.path))),
    }
  }))
}

export async function loadUserTravelRecords(user: User): Promise<TravelRecord[]> {
  const db = requireDatabase()
  const snapshot = await getDocs(collection(db, 'users', user.uid, 'travel'))
  return snapshot.docs.map((travelDoc) => {
    const data = travelDoc.data()
    return { ...data, id: travelDoc.id, savedAt: toIsoDate(data.savedAt) } as TravelRecord
  })
}

export async function saveUserTravelRecords(user: User, records: TravelRecord[]): Promise<void> {
  const db = requireDatabase()
  await Promise.all(records.map((record) => {
    const travelRef = doc(db, 'users', user.uid, 'travel', record.id)
    const { id, ...metadata } = record
    return setDoc(travelRef, metadata)
  }))
}
