import AppKit

// Keep the normal window size where possible and center it inside the destination's
// usable area, including displays above or to the left of the primary display.
func frameOnDisplay(_ frame: NSRect, visibleFrame: NSRect) -> NSRect {
  let size = NSSize(width: min(frame.width, visibleFrame.width),
    height: min(frame.height, visibleFrame.height))
  return NSRect(x: visibleFrame.midX - size.width / 2,
    y: visibleFrame.midY - size.height / 2, width: size.width, height: size.height)
}

extension HudApp: NSMenuDelegate {
  func menuNeedsUpdate(_ menu: NSMenu) {
    guard menu === windowMenu else { return }
    menu.removeAllItems()
    menu.addItem(withTitle: "Show Hud", action: #selector(showFromWindowMenu), keyEquivalent: "").target = self
    menu.addItem(withTitle: "Expand / Restore Hud", action: #selector(zoom), keyEquivalent: "").target = self
    let move = NSMenu(title: "Move to Display")
    let parent = menu.addItem(withTitle: "Move to Display", action: nil, keyEquivalent: "")
    parent.submenu = move
    for (index, screen) in NSScreen.screens.enumerated() {
      let item = move.addItem(withTitle: "\(index + 1): \(screen.localizedName)",
        action: #selector(moveToDisplay(_:)), keyEquivalent: "")
      item.target = self
      item.representedObject = screen.deviceDescription[NSDeviceDescriptionKey("NSScreenNumber")]
      item.state = window?.screen === screen ? .on : .off
    }
  }

  @objc func showFromWindowMenu() { show() }

  @objc func moveToDisplay(_ sender: NSMenuItem) {
    // Resolve the display again: it may have been unplugged while the menu was open.
    guard let id = sender.representedObject as? NSNumber,
      let screen = NSScreen.screens.first(where: {
        ($0.deviceDescription[NSDeviceDescriptionKey("NSScreenNumber")] as? NSNumber) == id
      }) else { return }
    moveWindow(to: screen)
  }

  func moveWindow(to screen: NSScreen) {
    // Moving an expanded window restores its saved normal dimensions on the target.
    let frame = window.isZoomed ? normalFrame : window.frame
    restoring = true
    if window.isZoomed { window.zoom(nil) }
    let destination = frameOnDisplay(frame, visibleFrame: screen.visibleFrame)
    window.setFrame(destination, display: true)
    normalFrame = window.frame
    restoring = false
    save()
    show()
    restoreTerminalFocus()
  }
}
