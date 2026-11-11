import AppKit
import HudCore

final class HudSetupPanel: HudSurface {
  unowned let app: HudApp
  let scroll = NSScrollView(), content = HudSurface()
  let path = NSTextField()
  let autoHide = NSButton(checkboxWithTitle: "Automatically hide when clicking outside Hud", target: nil, action: nil)
  let groups = [HudSurface(), HudSurface(), HudSurface()]
  var labels: [NSTextField] = []
  var buttons: [HudButton] = []
  init(app: HudApp) {
    self.app = app
    super.init(frame:.zero)
    scroll.documentView = content; scroll.hasVerticalScroller = true
    scroll.autohidesScrollers = true; scroll.drawsBackground = false; addSubview(scroll)
    for group in groups { content.addSubview(group) }
    func label(_ text:String, _ frame:NSRect, _ parent:NSView, bold:Bool = false) {
      let label = NSTextField(wrappingLabelWithString:text); label.font = HudStyle.font(14,bold:bold)
      label.frame = frame; label.autoresizingMask = [.width]; parent.addSubview(label); labels.append(label)
    }
    func button(_ text:String,_ frame:NSRect,_ parent:NSView,_ target:AnyObject,_ action:Selector) {
      let button = HudButton(text,target:target,action:action); button.frame = frame; parent.addSubview(button); buttons.append(button)
    }
    for (i,title) in ["Appearance","Floating H","Herdr connection"].enumerated() {
      label(title,NSRect(x:12,y:0,width:200,height:22),groups[i])
    }
    button("Choose theme…",NSRect(x:12,y:12,width:148,height:34),groups[0],app,#selector(HudApp.chooseTheme))
    label("Click H to show or hide Hud. Drag it anywhere on your desktop; its position is saved.",NSRect(x:12,y:12,width:350,height:40),groups[1])
    label("Use your existing Herdr installation. Tested with Herdr 0.9.1 and 0.9.5.",NSRect(x:12,y:95,width:350,height:40),groups[2])
    path.placeholderString = "Automatic, or choose the Herdr executable"
    path.stringValue = app.prefs.herdrPath; path.font = HudStyle.font(14)
    path.target = self; path.action = #selector(retry); groups[2].addSubview(path)
    button("Browse…",NSRect(x:12,y:12,width:90,height:34),groups[2],self,#selector(browse))
    button("Retry",NSRect(x:108,y:12,width:72,height:34),groups[2],self,#selector(retry))
    button("Install Herdr",NSRect(x:186,y:12,width:122,height:34),groups[2],self,#selector(install))
    button("Check for updates",NSRect(x:190,y:12,width:150,height:34),content,app,#selector(HudApp.checkForUpdates))
    button("Back to terminals",NSRect(x:18,y:12,width:165,height:34),content,app,#selector(HudApp.leaveSetup))
    autoHide.target = app; autoHide.action = #selector(HudApp.toggleAutoHide(_:))
    autoHide.state = app.prefs.autoHide ? .on : .off; groups[1].addSubview(autoHide)
    refresh()
  }
  required init?(coder:NSCoder) { fatalError() }
  override func layout() {
    super.layout(); scroll.frame = bounds
    content.frame = NSRect(x:0,y:0,width:scroll.contentSize.width,height:max(440,scroll.contentSize.height))
    let width = max(0,content.bounds.width-36), top = content.bounds.height-18
    for (i,geometry) in [(0,(top-80,CGFloat(80))),(1,(top-188,CGFloat(94))),(2,(top-374,CGFloat(172)))] {
      let group = groups[i]; group.frame = NSRect(x:18,y:geometry.0,width:width,height:geometry.1)
      group.subviews[0].frame = NSRect(x:12,y:group.bounds.height-25,width:width-24,height:22)
    }
    groups[1].subviews[1].frame = NSRect(x:12,y:35,width:max(0,width-24),height:32)
    autoHide.frame = NSRect(x:12,y:8,width:max(0,width-24),height:22)
    groups[2].subviews[1].frame.size.width = max(0,width-24)
    path.frame = NSRect(x:12,y:58,width:max(0,width-24),height:28)
    buttons.suffix(2).forEach { $0.frame.origin.y = top-424 }
  }
  func refresh() {
    fill = HudStyle.background; content.fill = HudStyle.background
    groups.forEach { $0.fill = HudStyle.background; $0.border = HudStyle.line }
    labels.forEach { $0.textColor = HudStyle.foreground }
    path.textColor = HudStyle.foreground; path.backgroundColor = HudStyle.side
    buttons.forEach { $0.needsDisplay = true }
  }
  @objc func browse() {
    let panel = NSOpenPanel(); panel.canChooseDirectories = false; panel.allowsMultipleSelection = false
    panel.message = "Choose the Herdr executable"
    if panel.runModal() == .OK, let url = panel.url { path.stringValue = url.path }
  }
  @objc func retry() {
    app.prefs.herdrPath = path.stringValue.trimmingCharacters(in:.whitespacesAndNewlines)
    app.save(); app.startBackend()
  }
  @objc func install() { NSWorkspace.shared.open(URL(string:"https://herdr.dev/docs/install/")!) }
}

final class PaletteCard: NSButton {
  override var isFlipped:Bool { false }
  let key: String, palette: Palette
  var selected = false, dark = true
  init(key:String,palette:Palette,target:AnyObject,action:Selector) {
    self.key = key; self.palette = palette
    super.init(frame:.zero); self.target = target; self.action = action
    title = palette.name; isBordered = false; setAccessibilityLabel(palette.name)
  }
  required init?(coder:NSCoder) { fatalError() }
  override func draw(_ rect:NSRect) {
    let colors = dark ? palette.dark : palette.light
    let background = NSColor(hex:colors.background), foreground = NSColor(hex:colors.foreground)
    let card = NSBezierPath(roundedRect:bounds.insetBy(dx:2,dy:2),xRadius:14,yRadius:14)
    background.setFill(); card.fill()
    (selected ? NSColor(hex:"#3584e4") : HudStyle.blend(background,foreground,0.22)).setStroke()
    card.lineWidth = selected ? 2 : 1; card.stroke()
    (palette.name as NSString).draw(in:NSRect(x:16,y:bounds.height-38,width:bounds.width-44,height:23),withAttributes:[.font:HudStyle.font(14,bold:true),.foregroundColor:foreground])
    if selected { ("✓" as NSString).draw(at:NSPoint(x:bounds.width-30,y:bounds.height-34),withAttributes:[.font:HudStyle.font(15,bold:true),.foregroundColor:foreground]) }
    ("The quick brown\nfox jumps over\nthe lazy dog" as NSString).draw(in:NSRect(x:16,y:38,width:bounds.width-32,height:66),withAttributes:[.font:HudStyle.mono(16),.foregroundColor:foreground])
    for i in 0..<6 {
      NSColor(hex:colors.colors[i+1]).setFill()
      NSBezierPath(roundedRect:NSRect(x:16+CGFloat(i)*(bounds.width-36)/6,y:17,width:(bounds.width-36)/6-4,height:12),xRadius:2,yRadius:2).fill()
    }
  }
}
final class PaletteGrid: NSView {
  override var isFlipped:Bool { true }
  var cards:[PaletteCard] = []
  func arrange(width:CGFloat) {
    let columns = max(1, min(3, Int((width+12)/212))), gap:CGFloat = 12
    let cardWidth = max(180,(width-CGFloat(columns-1)*gap)/CGFloat(columns))
    frame = NSRect(x:0,y:0,width:width,height:CGFloat((cards.count+columns-1)/columns)*162)
    for (index,card) in cards.enumerated() {
      card.frame = NSRect(x:CGFloat(index%columns)*(cardWidth+gap),y:CGFloat(index/columns)*162,width:cardWidth,height:150)
    }
  }
}
final class AppearanceSurface: HudSurface {
  var onLayout:(() -> Void)?
  override func layout() { super.layout(); onLayout?() }
}
final class SettingsController: NSWindowController, NSSearchFieldDelegate {
  unowned let app: HudApp
  let root = AppearanceSurface(), header = HudHeader(), search = HudSearchField(frame:.zero)
  let heading = NSTextField(labelWithString:"Appearance"), caption = NSTextField(labelWithString:"Appearance mode")
  let summary = NSTextField(labelWithString:""), note = NSTextField(labelWithString:"Palettes change Hud and its terminals. Your CLI theme is unchanged.")
  let mode = NSPopUpButton(), showAll = NSButton(checkboxWithTitle:"Show all palettes",target:nil,action:nil)
  let scroll = NSScrollView(), grid = PaletteGrid()
  var done:HudButton!, close:HudButton!
  var keys:[String] = []
  init(app:HudApp) {
    self.app = app
    let window = NSWindow(contentRect:NSRect(x:0,y:0,width:790,height:650),styleMask:[.titled,.closable,.resizable,.fullSizeContentView],backing:.buffered,defer:false)
    window.title = "Appearance"; window.titleVisibility = .hidden; window.titlebarAppearsTransparent = true
    for type in [NSWindow.ButtonType.closeButton,.miniaturizeButton,.zoomButton] { window.standardWindowButton(type)?.isHidden = true }
    window.minSize = NSSize(width:510,height:420); window.isReleasedWhenClosed = false; window.level = .floating
    window.center(); super.init(window:window); window.contentView = root
    done = HudButton("Done",target:self,action:#selector(dismiss))
    close = HudButton("×",target:self,action:#selector(dismiss))
    heading.font = HudStyle.font(16,bold:true); heading.alignment = .center
    caption.font = HudStyle.font(14); summary.font = HudStyle.font(14); note.font = HudStyle.font(11)
    mode.addItems(withTitles:["Follow desktop","Light","Dark"]); mode.font = HudStyle.font(14)
    mode.target = self; mode.action = #selector(changeAppearanceMode)
    showAll.font = HudStyle.font(14); showAll.target = self; showAll.action = #selector(filter)
    search.placeholderString = "Find a theme…"; search.delegate = self; search.sendsSearchStringImmediately = true
    scroll.documentView = grid; scroll.hasVerticalScroller = true; scroll.autohidesScrollers = true; scroll.scrollerStyle = .overlay; scroll.drawsBackground = false
    for view in [header,caption,mode,showAll,search,summary,scroll,note,done!] { root.addSubview(view) }
    header.addSubview(heading); header.addSubview(close)
    root.onLayout = { [weak self] in self?.layout() }
    syncAppearance()
  }
  required init?(coder:NSCoder) { fatalError() }
  func layout() {
    let w = root.bounds.width, h = root.bounds.height
    header.frame = NSRect(x:0,y:h-46,width:w,height:46)
    heading.frame = NSRect(x:w/2-90,y:12,width:180,height:25); close.frame = NSRect(x:w-40,y:6,width:34,height:34)
    caption.frame = NSRect(x:20,y:h-92,width:140,height:24)
    mode.frame = NSRect(x:166,y:h-94,width:170,height:30)
    showAll.frame = NSRect(x:w-195,y:h-92,width:175,height:24)
    search.frame = NSRect(x:20,y:h-144,width:w-40,height:34)
    summary.frame = NSRect(x:20,y:h-180,width:w-40,height:24)
    scroll.frame = NSRect(x:20,y:73,width:w-40,height:max(0,h-265))
    grid.arrange(width:scroll.contentSize.width)
    note.frame = NSRect(x:20,y:19,width:max(0,w-130),height:28)
    done.frame = NSRect(x:w-100,y:18,width:80,height:34)
  }
  func syncAppearance() {
    window?.appearance = app.window.appearance; window?.backgroundColor = HudStyle.background
    root.fill = HudStyle.background; header.fill = HudStyle.side; header.border = HudStyle.line
    for label in [heading,caption,summary,note] { label.textColor = HudStyle.foreground }
    search.textColor = HudStyle.foreground; search.needsDisplay = true
    done.needsDisplay = true; close.needsDisplay = true
    mode.selectItem(at:["system","light","dark"].firstIndex(of:app.prefs.appearance) ?? 2)
    filter()
  }
  @objc func changeAppearanceMode() {
    app.prefs.appearance = ["system","light","dark"][mode.indexOfSelectedItem]; app.applyTheme()
  }
  @objc func filter() {
    let query = search.stringValue.trimmingCharacters(in:.whitespacesAndNewlines)
    keys = app.palettes.keys.filter {
      let palette = app.palettes[$0]!
      return query.isEmpty ? (showAll.state == .on || palette.primary == true || $0 == app.prefs.palette || $0 == "hud") : palette.name.localizedCaseInsensitiveContains(query)
    }.sorted { app.palettes[$0]!.name.localizedStandardCompare(app.palettes[$1]!.name) == .orderedAscending }
    grid.cards.forEach { $0.removeFromSuperview() }
    grid.cards = keys.map { key in
      let card = PaletteCard(key:key,palette:app.palettes[key]!,target:self,action:#selector(selectPalette(_:)))
      card.selected = key == app.prefs.palette; card.dark = HudStyle.dark; grid.addSubview(card); return card
    }
    summary.stringValue = "\(app.palettes[app.prefs.palette]?.name ?? app.prefs.palette) selected · \(keys.count) themes"
    layout()
  }
  @objc func selectPalette(_ sender:PaletteCard) { app.prefs.palette = sender.key; app.applyTheme() }
  @objc func dismiss() { window?.orderOut(nil); app.show() }
  func controlTextDidChange(_ obj:Notification) { filter() }
}
