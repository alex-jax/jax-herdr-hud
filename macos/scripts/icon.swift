import AppKit

let destination = CommandLine.arguments[1]
var icns = Data("icns".utf8)
icns.append(contentsOf: [0, 0, 0, 0])
for (size, type) in [
  (16, "icp4"), (32, "icp5"), (64, "icp6"), (128, "ic07"), (256, "ic08"), (512, "ic09"),
  (1024, "ic10"),
] {
  let image = NSImage(size: NSSize(width: size, height: size))
  image.lockFocus()
  let scale = CGFloat(size) / 128
  NSColor(calibratedWhite: 0.15, alpha: 1).setFill()
  let path = NSBezierPath(
    ovalIn: NSRect(x: 8 * scale, y: 8 * scale, width: 112 * scale, height: 112 * scale))
  path.fill()
  NSColor.systemBlue.setStroke()
  path.lineWidth = 6 * scale
  path.stroke()
  let attrs: [NSAttributedString.Key: Any] = [
    .font: NSFont.systemFont(ofSize: 72 * scale, weight: .semibold),
    .foregroundColor: NSColor.white,
  ]
  let h = "H" as NSString
  let s = h.size(withAttributes: attrs)
  h.draw(
    at: NSPoint(x: (CGFloat(size) - s.width) / 2, y: (CGFloat(size) - s.height) / 2),
    withAttributes: attrs)
  image.unlockFocus()
  let png = NSBitmapImageRep(data: image.tiffRepresentation!)!.representation(
    using: .png, properties: [:])!
  icns.append(Data(type.utf8))
  var length = UInt32(png.count + 8).bigEndian
  withUnsafeBytes(of: &length) { icns.append(contentsOf: $0) }
  icns.append(png)
}
var total = UInt32(icns.count).bigEndian
withUnsafeBytes(of: &total) { icns.replaceSubrange(4..<8, with: $0) }
try icns.write(to: URL(fileURLWithPath: destination))
