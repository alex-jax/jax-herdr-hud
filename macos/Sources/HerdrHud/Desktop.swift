import AppKit
import HudCore

func clampedFrame(_ frame: NSRect, fallback: NSRect) -> NSRect {
  let screens = NSScreen.screens.map(\.visibleFrame)
  guard let first = screens.first else { return frame }
  let valid =
    frame.width.isFinite && frame.height.isFinite && frame.origin.x.isFinite
    && frame.origin.y.isFinite && frame.width > 0 && frame.height > 0
  var rect = valid ? frame : fallback
  let screen = screens.max { $0.intersection(rect).area < $1.intersection(rect).area } ?? first
  rect.size.width = min(rect.width, screen.width)
  rect.size.height = min(rect.height, screen.height)
  rect.origin.x = min(max(rect.minX, screen.minX), screen.maxX - rect.width)
  rect.origin.y = min(max(rect.minY, screen.minY), screen.maxY - rect.height)
  return rect
}
extension NSRect { fileprivate var area: CGFloat { isNull ? 0 : width * height } }
func frameArray(_ frame: NSRect) -> [Double] {
  [frame.minX, frame.minY, frame.width, frame.height]
}
func storedFrame(_ values: [Double], fallback: NSRect) -> NSRect {
  values.count == 4
    ? clampedFrame(
      NSRect(x: values[0], y: values[1], width: values[2], height: values[3]), fallback: fallback)
    : fallback
}

final class BubblePanel: NSPanel {
  override var canBecomeKey: Bool { true }
  override var canBecomeMain: Bool { false }
}
final class BubbleView: NSView {
  var toggle: (() -> Void)?
  var moved: (() -> Void)?
  var unread = 0 { didSet { setAccessibilityLabel("Herdr Hud, \(unread) unread terminals. Click to open, drag to move."); needsDisplay = true } }
  private var downEvent: NSEvent?
  var isInteracting: Bool { downEvent != nil }
  private var original: NSPoint?
  private var nativeDrag = false
  private var cancelled = false
  private var releaseWatch: Timer?
  override var acceptsFirstResponder: Bool { true }
  override var mouseDownCanMoveWindow: Bool { false }
  override func acceptsFirstMouse(for event: NSEvent?) -> Bool { true }
  override func shouldDelayWindowOrdering(for event: NSEvent) -> Bool { false }
  override init(frame: NSRect) {
    super.init(frame: frame)
    setAccessibilityElement(true); setAccessibilityRole(.button)
    setAccessibilityLabel("Herdr Hud — click to open, drag to move")
    toolTip = "Click to show or hide Hud. Drag to move."
  }
  required init?(coder: NSCoder) { fatalError() }
  override func draw(_ dirtyRect: NSRect) {
    let circle = NSBezierPath(ovalIn: bounds.insetBy(dx:1,dy:1))
    (HudStyle.dark ? NSColor(hex:"#303030") : NSColor(hex:"#fafafa")).setFill(); circle.fill()
    NSColor.controlAccentColor.setStroke(); circle.lineWidth = 2; circle.stroke()
    let text = "H" as NSString
    let attrs: [NSAttributedString.Key: Any] = [.font:HudStyle.font(27,bold:true),.foregroundColor:HudStyle.dark ? NSColor.white : NSColor(hex:"#303030")]
    let size = text.size(withAttributes:attrs)
    text.draw(at:NSPoint(x:(bounds.width-size.width)/2,y:(bounds.height-size.height)/2),withAttributes:attrs)
    if unread > 0 {
      let badge = NSBezierPath(ovalIn:NSRect(x:bounds.width-14,y:bounds.height-14,width:13,height:13))
      NSColor(hex:"#3584e4").setFill(); badge.fill(); NSColor.white.setStroke(); badge.lineWidth = 2; badge.stroke()
    }
  }
  override func accessibilityPerformPress() -> Bool { toggle?(); return true }
  override func mouseDown(with event: NSEvent) {
    guard downEvent == nil else { return }
    downEvent = event; original = window?.frame.origin; nativeDrag = false; cancelled = false
    window?.makeFirstResponder(self)
  }
  override func mouseDragged(with event: NSEvent) {
    guard !nativeDrag, !cancelled, let downEvent, let window else { return }
    let delta = hypot(event.locationInWindow.x-downEvent.locationInWindow.x,event.locationInWindow.y-downEvent.locationInWindow.y)
    guard delta >= 3 else { return }
    nativeDrag = true
    // Let WindowServer track the drag across monitors and Spaces. Inactive panels
    // must accept the initial click; making the panel key mid-press loses the drag.
    window.performDrag(with:downEvent)
    // performDrag returns immediately and does not guarantee mouseUp delivery.
    let timer = Timer(timeInterval:1.0/60,repeats:true) { [weak self] _ in
      guard let self else { return }
      if NSEvent.pressedMouseButtons & 1 == 0 { self.finishDrag() }
    }
    releaseWatch = timer
    RunLoop.main.add(timer,forMode:.common)
  }
  override func mouseUp(with event: NSEvent) {
    if nativeDrag { finishDrag() }
    else {
      let click = downEvent != nil && !cancelled
      clearTracking()
      if click { toggle?() }
    }
  }
  private func finishDrag() {
    guard downEvent != nil, let window else { clearTracking(); return }
    if cancelled, let original { window.setFrameOrigin(original) }
    window.setFrame(clampedFrame(window.frame,fallback:window.frame),display:true)
    clearTracking(); moved?()
  }
  private func clearTracking() { releaseWatch?.invalidate(); releaseWatch = nil; downEvent = nil; original = nil; nativeDrag = false; cancelled = false }
  func cancelDrag() { if let original { window?.setFrameOrigin(original) }; cancelled = true; if !nativeDrag { clearTracking() } }
  override func viewWillMove(toWindow newWindow: NSWindow?) { if newWindow == nil { clearTracking() }; super.viewWillMove(toWindow:newWindow) }
  override func keyDown(with event: NSEvent) {
    if event.keyCode == 53 { cancelDrag() }
    else if [36,49,76].contains(event.keyCode) { toggle?() }
    else { super.keyDown(with:event) }
  }
}

final class Row: NSObject {
  let session: SessionBox
  let workspace: String
  let terminal: String?
  let title: String
  let status: String
  let collapsed: Bool
  let subtitle: String
  init(
    session: SessionBox, workspace: String, terminal: String?, title: String, status: String,
    collapsed: Bool = false, subtitle: String = ""
  ) {
    self.session = session
    self.workspace = workspace
    self.terminal = terminal
    self.title = title
    self.status = status
    self.collapsed = collapsed
    self.subtitle = subtitle
  }
  var identity: String { session.value.socket_path + "|" + (terminal ?? "space:" + workspace) }
}
final class SessionBox {
  let value: Session
  init(_ value: Session) { self.value = value }
}
final class SidebarTable: NSTableView {
  var context: ((Int) -> NSMenu?)?
  override func menu(for event: NSEvent) -> NSMenu? {
    context?(row(at: convert(event.locationInWindow, from: nil)))
  }
}
final class SidebarCell: NSTableCellView {
  var identityText: String?
  private var identityPopover: NSPopover?
  private var identityDelay: DispatchWorkItem?

  let label = NSTextField(labelWithString: "")
  let subtitle = NSTextField(labelWithString: "")
  let dot = NSTextField(labelWithString: "●")
  let disclosure = HudButton("",glyph:"down",target:nil,action:nil)
  let plus = HudButton("",glyph:"plus",target:nil,action:nil)
  let pencil = HudButton("",glyph:"pencil",target:nil,action:nil)
  var expand: (() -> Void)?
  var add: (() -> Void)?
  var actions: (() -> Void)?
  var group = false
  var agentShortcut = false
  private var tracking: NSTrackingArea?
  override init(frame:NSRect) {
    super.init(frame:frame)
    disclosure.target = self; disclosure.action = #selector(expandClicked)
    plus.target = self; plus.action = #selector(addClicked)
    pencil.target = self; pencil.action = #selector(actionsClicked)
    disclosure.setAccessibilityLabel("Expand or collapse space"); plus.setAccessibilityLabel("New terminal in space"); pencil.setAccessibilityLabel("Rename or close")
    label.lineBreakMode = .byTruncatingTail; subtitle.lineBreakMode = .byTruncatingTail
    label.font = HudStyle.font(14); subtitle.font = HudStyle.font(11); dot.font = HudStyle.font(14)
    pencil.isHidden = true
    for view in [disclosure,dot,label,subtitle,pencil,plus] { addSubview(view) }
  }
  required init?(coder:NSCoder) { fatalError() }
  override func updateTrackingAreas() {
    super.updateTrackingAreas(); if let tracking { removeTrackingArea(tracking) }
    tracking = NSTrackingArea(rect:bounds,options:[.activeAlways,.mouseEnteredAndExited,.inVisibleRect],owner:self); addTrackingArea(tracking!)
  }
  override func mouseEntered(with event:NSEvent) {
    pencil.isHidden = false
    identityDelay?.cancel()
    let work = DispatchWorkItem { [weak self] in
      guard let self, let text = self.identityText, self.window != nil else { return }
      let content = HudSurface(frame:NSRect(x:0,y:0,width:260,height:40))
      content.fill = HudStyle.background; content.border = HudStyle.line
      let label = NSTextField(labelWithString:text); label.textColor = HudStyle.foreground
      label.font = HudStyle.font(12); label.frame = NSRect(x:10,y:10,width:240,height:20)
      content.addSubview(label)
      let controller = NSViewController(); controller.view = content
      let popover = NSPopover(); popover.contentViewController = controller
      popover.behavior = .transient; popover.animates = false
      self.identityPopover = popover
      popover.show(relativeTo:self.bounds,of:self,preferredEdge:.maxX)
    }
    identityDelay = work; DispatchQueue.main.asyncAfter(deadline:.now()+0.5,execute:work)
  }
  override func mouseExited(with event:NSEvent) { identityDelay?.cancel(); identityPopover?.close(); pencil.isHidden = true }
  override func draw(_ rect:NSRect) {
    if !group && !agentShortcut { HudStyle.line.setFill(); NSRect(x:18,y:0,width:1,height:bounds.height).fill() }
  }
  override func layout() {
    super.layout()
    let cy = group ? (bounds.height-8)/2 : agentShortcut ? bounds.height-15 : bounds.height/2
    disclosure.frame = NSRect(x:6,y:cy-10,width:18,height:21)
    dot.frame = NSRect(x:group ? 56 : agentShortcut ? 34 : 56,y:cy-9,width:14,height:20)
    let left:CGFloat = group ? 76 : agentShortcut ? 52 : 76
    label.frame = NSRect(x:left,y:cy-10,width:max(0,bounds.width-left-(group ? 35:8)),height:22)
    plus.frame = NSRect(x:bounds.width-34,y:cy-11,width:28,height:23)
    pencil.frame = NSRect(x:group ? 30 : agentShortcut ? 7 : 29,y:cy-9,width:19,height:19)
    subtitle.frame = NSRect(x:6,y:1,width:max(0,bounds.width-12),height:17)
    subtitle.isHidden = !agentShortcut
  }
  @objc private func expandClicked() { expand?() }
  @objc private func addClicked() { add?() }
  @objc private func actionsClicked() { actions?() }
}
