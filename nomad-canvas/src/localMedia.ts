import type { AlbumMedia } from './models'

type StoredAlbumMedia = {
  albumId: string
  files: Array<{ name: string; contentType: string; blob: Blob }>
}

const databaseName = 'roam-make-media'
const storeName = 'albums'

function openMediaDatabase(): Promise<IDBDatabase> {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open(databaseName, 1)
    request.onupgradeneeded = () => {
      request.result.createObjectStore(storeName, { keyPath: 'albumId' })
    }
    request.onsuccess = () => resolve(request.result)
    request.onerror = () => reject(request.error ?? new Error('Could not open local video storage.'))
  })
}

export async function saveLocalAlbumMedia(albumId: string, files: File[]): Promise<AlbumMedia[]> {
  const database = await openMediaDatabase()
  try {
    await new Promise<void>((resolve, reject) => {
      const transaction = database.transaction(storeName, 'readwrite')
      transaction.objectStore(storeName).put({
        albumId,
        files: files.map((file) => ({ name: file.name, contentType: file.type, blob: file })),
      } satisfies StoredAlbumMedia)
      transaction.oncomplete = () => resolve()
      transaction.onerror = () => reject(transaction.error ?? new Error('Could not save videos to local storage.'))
      transaction.onabort = () => reject(transaction.error ?? new Error('Video storage transaction was cancelled.'))
    })
    return files.map((file, index) => ({
      name: file.name,
      contentType: file.type,
      path: `local:${albumId}:${index}`,
    }))
  } finally {
    database.close()
  }
}

export async function loadLocalAlbumMedia(albumId: string, count = Number.POSITIVE_INFINITY): Promise<Array<AlbumMedia & { url: string }>> {
  const database = await openMediaDatabase()
  try {
    const stored = await new Promise<StoredAlbumMedia | undefined>((resolve, reject) => {
      const request = database.transaction(storeName, 'readonly').objectStore(storeName).get(albumId)
      request.onsuccess = () => resolve(request.result as StoredAlbumMedia | undefined)
      request.onerror = () => reject(request.error ?? new Error('Could not load locally saved videos.'))
    })
    return (stored?.files ?? []).slice(0, count).map((file, index) => ({
      name: file.name,
      contentType: file.contentType,
      path: `local:${albumId}:${index}`,
      url: URL.createObjectURL(file.blob),
    }))
  } finally {
    database.close()
  }
}
