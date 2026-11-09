// Local review utility: reads only the explicitly listed demo videos, never Photos metadata.
import Foundation
import AppKit
import AVFoundation

let args = CommandLine.arguments
guard args.count == 4 else { fatalError("Usage: video_contact_sheet manifest.json originals-directory output.png") }
let data = try Data(contentsOf: URL(fileURLWithPath: args[1]))
let manifest = try JSONSerialization.jsonObject(with: data) as! [String: Any]
let ids = manifest["video_ids"] as! [String]
let width = 192, height = 150, columns = 8
let rows = Int(ceil(Double(ids.count) / Double(columns)))
let sheet = NSImage(size: NSSize(width: width * columns, height: height * rows))
sheet.lockFocus()
NSColor(calibratedWhite: 0.1, alpha: 1).setFill()
NSRect(x: 0, y: 0, width: width * columns, height: height * rows).fill()
for (index, id) in ids.enumerated() {
    let file = URL(fileURLWithPath: args[2]).appendingPathComponent(String(id.prefix(1))).appendingPathComponent(id + ".mov")
    let asset = AVURLAsset(url: file)
    let generator = AVAssetImageGenerator(asset: asset)
    generator.appliesPreferredTrackTransform = true
    generator.maximumSize = CGSize(width: 190, height: 120)
    let x = (index % columns) * width, y = (rows - 1 - index / columns) * height
    do {
        let cg = try generator.copyCGImage(at: CMTime(seconds: 0.25, preferredTimescale: 600), actualTime: nil)
        let image = NSImage(cgImage: cg, size: NSSize(width: cg.width, height: cg.height))
        let scale = min(190.0 / Double(cg.width), 120.0 / Double(cg.height))
        let w = Double(cg.width) * scale, h = Double(cg.height) * scale
        image.draw(in: NSRect(x: Double(x) + (192-w)/2, y: Double(y)+26+(120-h)/2, width: w, height: h))
        print(String(format: "%02d", index+1), id, "OK")
    } catch { print(String(format: "%02d", index+1), id, "UNAVAILABLE", error.localizedDescription) }
    let label = String(format: "%02d", index+1) + "  " + String(id.prefix(8))
    (label as NSString).draw(at: NSPoint(x: x+8, y: y+5), withAttributes: [.font: NSFont.monospacedSystemFont(ofSize: 12, weight: .medium), .foregroundColor: NSColor.white])
}
sheet.unlockFocus()
let bitmap = NSBitmapImageRep(data: sheet.tiffRepresentation!)!
try bitmap.representation(using: .png, properties: [:])!.write(to: URL(fileURLWithPath: args[3]))
