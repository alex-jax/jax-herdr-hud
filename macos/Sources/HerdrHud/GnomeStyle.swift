import AppKit
import CoreText

/// Metrics and color blends taken from hud.py, rather than platform control defaults.
enum HudStyle {
  static func registerFonts() {
    for name in ["Ubuntu-Regular", "Ubuntu-Bold", "UbuntuMono-Regular"] {
      if let url = Bundle.module.url(forResource: name, withExtension: "ttf", subdirectory: "Resources/Fonts") {
        CTFontManagerRegisterFontsForURL(url as CFURL, .process, nil)
      }
    }
  }
  static func font(_ size: CGFloat, bold: Bool = false) -> NSFont {
    NSFont(name: bold ? "Ubuntu-Bold" : "Ubuntu-Regular", size: size) ?? .systemFont(ofSize: size, weight: bold ? .bold : .regular)
  }
  static func mono(_ size: CGFloat = 16) -> NSFont {
    NSFont(name: "UbuntuMono-Regular", size: size) ?? .monospacedSystemFont(ofSize: size, weight: .regular)
  }
  static var foreground = NSColor(hex: "#d8dee9")
  static var background = NSColor(hex: "#2e3440")
  static var side = NSColor(hex: "#373e4b")
  static var line = NSColor(hex: "#535d6f")
  static var hover = NSColor(hex: "#434c5e")
  static var selected = NSColor(hex: "#4a596b")
  static var dark = true
  static func apply(_ colors: PaletteVariant, dark: Bool) {
    self.dark = dark
    foreground = NSColor(hex: colors.foreground); background = NSColor(hex: colors.background)
    side = blend(background, foreground, 0.055); line = blend(background, foreground, 0.22)
    hover = blend(background, foreground, 0.12)
    selected = blend(background, NSColor(hex: colors.colors[4]), 0.35)
  }
  static func blend(_ a: NSColor, _ b: NSColor, _ t: CGFloat) -> NSColor {
    let a = a.usingColorSpace(.sRGB)!, b = b.usingColorSpace(.sRGB)!
    return NSColor(srgbRed:a.redComponent*(1-t)+b.redComponent*t, green:a.greenComponent*(1-t)+b.greenComponent*t, blue:a.blueComponent*(1-t)+b.blueComponent*t, alpha:1)
  }
}

class HudSurface: NSView {
  var fill: NSColor = .clear { didSet { needsDisplay = true } }
  var border: NSColor? { didSet { needsDisplay = true } }
  var radius: CGFloat = 0
  override func draw(_ rect: NSRect) {
    let path = NSBezierPath(roundedRect: bounds.insetBy(dx:0.5,dy:0.5), xRadius:radius, yRadius:radius)
    fill.setFill(); path.fill()
    if let border { border.setStroke(); path.lineWidth = 1; path.stroke() }
  }
}

final class HudHeader: HudSurface {
  override var mouseDownCanMoveWindow: Bool { true }
  override func mouseDown(with event: NSEvent) { window?.performDrag(with:event) }
}

final class HudButton: NSButton {
  override var isFlipped:Bool { false }
  var glyph: String?
  var showsBorder = true
  var hovered = false
  private var tracking: NSTrackingArea?
  override init(frame:NSRect) { super.init(frame:frame); isBordered = false; focusRingType = .none; font = HudStyle.font(14) }
  convenience init(_ title: String = "", glyph: String? = nil, target: AnyObject?, action: Selector?) {
    self.init(frame:.zero); self.title = title; self.glyph = glyph; self.target = target; self.action = action
  }
  required init?(coder:NSCoder) { fatalError() }
  override func updateTrackingAreas() {
    super.updateTrackingAreas(); if let tracking { removeTrackingArea(tracking) }
    tracking = NSTrackingArea(rect:bounds, options:[.activeAlways,.mouseEnteredAndExited,.inVisibleRect], owner:self)
    addTrackingArea(tracking!)
  }
  override func mouseEntered(with event:NSEvent) { hovered = true; needsDisplay = true }
  override func mouseExited(with event:NSEvent) { hovered = false; needsDisplay = true }
  override func draw(_ rect:NSRect) {
    let path = NSBezierPath(roundedRect:bounds.insetBy(dx:0.5,dy:0.5), xRadius:6, yRadius:6)
    (isHighlighted ? HudStyle.selected : hovered ? HudStyle.hover : showsBorder ? HudStyle.side : .clear).setFill(); path.fill()
    if showsBorder { HudStyle.line.setStroke(); path.lineWidth = 1; path.stroke() }
    let color = isEnabled ? HudStyle.foreground : HudStyle.line
    if let glyph { drawGlyph(glyph, in:bounds, color:color) }
    else {
      let text = NSAttributedString(string:title, attributes:[.font:font ?? HudStyle.font(14),.foregroundColor:color])
      let size = text.size(); text.draw(at:NSPoint(x:alignment == .left ? 3 : (bounds.width-size.width)/2,y:(bounds.height-size.height)/2))
    }
  }
  private func drawGlyph(_ glyph:String, in rect:NSRect, color:NSColor) {
    if ["left","right","down","plus","minus","power","expand","info","sun","moon"].contains(glyph) {
      let c = NSPoint(x:rect.midX,y:rect.midY), p = NSBezierPath(); p.lineWidth = 1.25; p.lineCapStyle = .round; p.lineJoinStyle = .round
      color.setStroke()
      switch glyph {
      case "left", "right", "down":
        let points:[NSPoint] = glyph == "left" ? [.init(x:c.x+2,y:c.y+4),.init(x:c.x-2,y:c.y),.init(x:c.x+2,y:c.y-4)] : glyph == "right" ? [.init(x:c.x-2,y:c.y+4),.init(x:c.x+2,y:c.y),.init(x:c.x-2,y:c.y-4)] : [.init(x:c.x-4,y:c.y+2),.init(x:c.x,y:c.y-2),.init(x:c.x+4,y:c.y+2)]
        p.move(to:points[0]); points.dropFirst().forEach { p.line(to:$0) }
      case "plus", "minus":
        p.move(to:.init(x:c.x-5,y:c.y)); p.line(to:.init(x:c.x+5,y:c.y))
        if glyph == "plus" { p.move(to:.init(x:c.x,y:c.y-5)); p.line(to:.init(x:c.x,y:c.y+5)) }
      case "power":
        p.appendArc(withCenter:c,radius:6,startAngle:55,endAngle:125,clockwise:true)
        p.move(to:.init(x:c.x,y:c.y+1)); p.line(to:.init(x:c.x,y:c.y+8))
      case "info":
        p.appendOval(in:NSRect(x:c.x-7,y:c.y-7,width:14,height:14)); p.move(to:.init(x:c.x,y:c.y-4)); p.line(to:.init(x:c.x,y:c.y+1)); p.appendOval(in:NSRect(x:c.x-0.5,y:c.y+4,width:1,height:1))
      case "expand":
        p.move(to:.init(x:c.x-6,y:c.y-1)); p.line(to:.init(x:c.x-6,y:c.y-6)); p.line(to:.init(x:c.x-1,y:c.y-6)); p.move(to:.init(x:c.x-6,y:c.y-6)); p.line(to:.init(x:c.x-1,y:c.y-1))
        p.move(to:.init(x:c.x+6,y:c.y+1)); p.line(to:.init(x:c.x+6,y:c.y+6)); p.line(to:.init(x:c.x+1,y:c.y+6)); p.move(to:.init(x:c.x+6,y:c.y+6)); p.line(to:.init(x:c.x+1,y:c.y+1))
      case "sun":
        p.appendOval(in:NSRect(x:c.x-4,y:c.y-4,width:8,height:8))
        for i in 0..<8 { let a = CGFloat(i) * .pi / 4; p.move(to:.init(x:c.x+6*cos(a),y:c.y+6*sin(a))); p.line(to:.init(x:c.x+8*cos(a),y:c.y+8*sin(a))) }
      case "moon":
        p.appendArc(withCenter:c,radius:7,startAngle:70,endAngle:290,clockwise:false)
        p.appendArc(withCenter:.init(x:c.x+4,y:c.y),radius:6,startAngle:245,endAngle:115,clockwise:true); p.close()
      default: break
      }; p.stroke()
    } else if let image = NSImage(systemSymbolName:glyph == "settings" ? "gearshape" : "pencil", accessibilityDescription:nil) {
      let configuration = NSImage.SymbolConfiguration(pointSize:15,weight:.regular).applying(.init(paletteColors:[color]))
      let tinted = image.withSymbolConfiguration(configuration) ?? image
      let r = NSRect(x:rect.midX-8,y:rect.midY-8,width:16,height:16)
      tinted.draw(in:r)
    }
  }
}

final class HudSplitView: NSSplitView {
  var width: CGFloat = 6
  override var dividerThickness: CGFloat { width }
  override func drawDivider(in rect:NSRect) { HudStyle.line.setFill(); rect.fill() }
}
final class HudRowView: NSTableRowView {
  var inset: CGFloat = 0
  override func drawSelection(in dirtyRect:NSRect) {
    HudStyle.selected.setFill(); NSRect(x:inset,y:0,width:bounds.width-inset,height:bounds.height).fill()
  }
  override var isEmphasized:Bool { get { false } set {} }
}

final class HudSidebar: HudSurface {
  let search: NSSearchField
  let sections: NSSplitView
  let create: HudButton
  init(search:NSSearchField,sections:NSSplitView,create:HudButton) {
    self.search = search; self.sections = sections; self.create = create
    super.init(frame:.zero); [search,sections,create].forEach { addSubview($0) }
  }
  required init?(coder:NSCoder) { fatalError() }
  override func layout() {
    super.layout()
    search.frame = NSRect(x:16,y:max(0,bounds.height-46),width:max(0,bounds.width-32),height:34)
    create.frame = NSRect(x:16,y:16,width:max(0,bounds.width-32),height:40)
    sections.frame = NSRect(x:4,y:68,width:max(0,bounds.width-8),height:max(0,bounds.height-126))
  }
}
final class HudTerminalPane: HudSurface {
  let title: NSTextField
  let terminalHost: NSView
  var setup: NSView? { didSet { needsLayout = true } }
  init(title:NSTextField,terminalHost:NSView) {
    self.title = title; self.terminalHost = terminalHost
    super.init(frame:.zero); addSubview(title); addSubview(terminalHost)
  }
  required init?(coder:NSCoder) { fatalError() }
  override func layout() {
    super.layout()
    title.frame = NSRect(x:16,y:bounds.height-36,width:max(0,bounds.width-32),height:23)
    terminalHost.frame = NSRect(x:16,y:12,width:max(0,bounds.width-32),height:max(0,bounds.height-61))
    setup?.frame = NSRect(x:0,y:0,width:bounds.width,height:max(0,bounds.height-45))
  }
}
final class HudSection: HudSurface {
  let heading: NSButton
  let scroll: NSScrollView
  init(heading:NSButton,scroll:NSScrollView) {
    self.heading = heading; self.scroll = scroll
    super.init(frame:NSRect(x:0,y:0,width:245,height:260)); addSubview(heading); addSubview(scroll)
  }
  required init?(coder:NSCoder) { fatalError() }
  override func layout() {
    super.layout(); heading.frame = NSRect(x:0,y:bounds.height-25,width:bounds.width,height:25)
    scroll.frame = NSRect(x:12,y:0,width:max(0,bounds.width-24),height:max(0,bounds.height-25))
    if let table = scroll.documentView as? NSTableView {
      table.frame.size.width = scroll.contentSize.width
      table.tableColumns.first?.width = scroll.contentSize.width
    }
  }
}

final class HudSearchCell: NSSearchFieldCell {
  override func searchTextRect(forBounds rect:NSRect) -> NSRect {
    NSRect(x:rect.minX+28,y:rect.midY-9,width:max(0,rect.width-54),height:20)
  }
  override func searchButtonRect(forBounds rect:NSRect) -> NSRect {
    NSRect(x:rect.minX+8,y:rect.midY-8,width:16,height:16)
  }
  override func cancelButtonRect(forBounds rect:NSRect) -> NSRect {
    NSRect(x:rect.maxX-24,y:rect.midY-8,width:16,height:16)
  }
}
final class HudSearchField: NSSearchField {
  override init(frame:NSRect) {
    super.init(frame:frame); cell = HudSearchCell(textCell:""); isEditable = true; isSelectable = true; cell?.isScrollable = true; isBezeled = false; isBordered = false; drawsBackground = false
    font = HudStyle.font(14); focusRingType = .none
  }
  required init?(coder:NSCoder) { fatalError() }
  override func draw(_ rect:NSRect) {
    let path = NSBezierPath(roundedRect:bounds.insetBy(dx:0.5,dy:0.5),xRadius:6,yRadius:6)
    HudStyle.side.setFill(); path.fill(); HudStyle.line.setStroke(); path.stroke()
    super.draw(rect)
  }
}
