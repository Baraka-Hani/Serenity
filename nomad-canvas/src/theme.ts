export type Theme = {
  primary: string
  secondary: string
  background: string
  ink: string
  energy: number
}

export const defaultTheme: Theme = {
  primary: '#ff6b45',
  secondary: '#bdd7b2',
  background: '#f3efe5',
  ink: '#161713',
  energy: 62,
}

const rgbToHex = (r: number, g: number, b: number) =>
  `#${[r, g, b].map((v) => Math.round(v).toString(16).padStart(2, '0')).join('')}`

export async function themeFromVideo(file: File): Promise<Theme> {
  const url = URL.createObjectURL(file)
  const video = document.createElement('video')
  video.muted = true
  video.playsInline = true
  video.preload = 'metadata'
  video.src = url

  try {
    await new Promise<void>((resolve, reject) => {
      video.onloadedmetadata = () => resolve()
      video.onerror = () => reject(new Error('This video could not be read.'))
    })

    video.currentTime = Math.min(Math.max(video.duration * 0.18, 0), 4)
    await new Promise<void>((resolve) => { video.onseeked = () => resolve() })

    const canvas = document.createElement('canvas')
    canvas.width = 48
    canvas.height = 48
    const ctx = canvas.getContext('2d', { willReadFrequently: true })!
    ctx.drawImage(video, 0, 0, 48, 48)
    const pixels = ctx.getImageData(0, 0, 48, 48).data

    let r = 0, g = 0, b = 0, weight = 0, variance = 0
    for (let i = 0; i < pixels.length; i += 16) {
      const brightness = (pixels[i] + pixels[i + 1] + pixels[i + 2]) / 3
      if (brightness > 18 && brightness < 242) {
        r += pixels[i]; g += pixels[i + 1]; b += pixels[i + 2]; weight++
        variance += Math.max(pixels[i], pixels[i + 1], pixels[i + 2]) - Math.min(pixels[i], pixels[i + 1], pixels[i + 2])
      }
    }
    if (!weight) return defaultTheme
    r /= weight; g /= weight; b /= weight
    const energy = Math.min(96, Math.max(28, Math.round(35 + variance / weight * .55)))
    const lift = (value: number, amount: number) => value + (255 - value) * amount
    const dark = (value: number) => value * .28

    return {
      primary: rgbToHex(lift(r, .12), lift(g, .12), lift(b, .12)),
      secondary: rgbToHex(lift(b, .48), lift(r, .48), lift(g, .48)),
      background: rgbToHex(lift(r, .9), lift(g, .9), lift(b, .9)),
      ink: rgbToHex(dark(r), dark(g), dark(b)),
      energy,
    }
  } finally {
    URL.revokeObjectURL(url)
  }
}
