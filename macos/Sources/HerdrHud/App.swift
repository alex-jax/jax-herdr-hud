import AppKit
import Carbon
import HudCore
import ServiceManagement

final class HudApp: NSObject, NSApplicationDelegate, NSWindowDelegate, NSTableViewDataSource,
  NSTableViewDelegate, NSSearchFieldDelegate, NSSplitViewDelegate
{
  var prefs = Preferences.load()
  var backend = Backend()
  var monitor: Monitor?
  let worker = DispatchQueue(label: "io.github.herdr.Hud.operations")
  var window: NSWindow!
  var bubble: BubblePanel!
  var bubbleView = BubbleView(frame: NSRect(x: 0, y: 0, width: 56, height: 56))
  var statusItem: NSStatusItem!
  let search = HudSearchField(frame:.zero)
  let status = NSTextField(labelWithString: "Connecting to Herdr…")
  let title = NSTextField(labelWithString: "Herdr Hud")
  let split = HudSplitView(), sections = HudSplitView()
  let spaces = SidebarTable(), agents = SidebarTable()
  let spaceToggle = HudButton(), agentToggle = HudButton()
  let emptyAgents = NSTextField(labelWithString: "No agents running")
  let terminalHost = NSView()
  var sidebar: HudSidebar!
  var rightPane: HudTerminalPane!
  let header = HudHeader()
  let appTitle = NSTextField(labelWithString:"Herdr Hud")
  let appSubtitle = NSTextField(labelWithString:"Your terminals, within reach")
  var sidebarToggle: HudButton!
  var themeButton: HudButton!
  var updateButton: HudButton!
  var updateTimer: Timer?
  var availableUpdate: HudRelease?
  var updateBusy = false
  var chromeButtons:[HudButton] = []
  var setupPanel: HudSetupPanel?
  var showingSetup = false
  var snapshots: [String: (Session, Snapshot)] = [:]
  var terminals: [TerminalKey: HudTerminal] = [:]
  var selected: TerminalKey?
  var previousStates: [TerminalKey: String] = [:]
  var unread = Set<TerminalKey>()
  var disconnected = Set<String>()
  var terminalIdentities: [TerminalKey: String] = [:]
  var collapsed = Set<SpaceKey>()
  var workspaceSelection: [SpaceKey: TerminalKey] = [:]
  var spaceRows: [Row] = [], agentRows: [Row] = []
  var normalized = Set<String>()
  var busy = false, closing = false, rebuilding = false, restoring = false
  var generation = 0
  var restoringSections = false
  var sidebarSaved: CGFloat = 245
  var settingsController: SettingsController?
  var palettes: [String: Palette] = [:]
  var observers: [NSObjectProtocol] = []
  var tooltip: NSPopover?
  var tooltipDismiss: DispatchWorkItem?
  var desktopActive = true
  var normalFrame: NSRect = .zero
  var outsideClickMonitor: Any?
  var menuTracking = 0
  let windowMenu = NSMenu(title: "Window")

  func applicationDidFinishLaunching(_ notification: Notification) {
    if CommandLine.arguments.contains("--quit") {
      NSApp.terminate(nil)
      return
    }
    backend = makeBackend()
    if let url = Bundle.module.url(
      forResource: "palettes", withExtension: "json", subdirectory: "Resources"),
      let data = try? Data(contentsOf: url)
    {
      palettes = (try? JSONDecoder().decode([String: Palette].self, from: data)) ?? [:]
    }
    installMenu()
    buildWindow()
    buildDesktop()
    outsideClickMonitor = NSEvent.addGlobalMonitorForEvents(matching: [.leftMouseDown, .rightMouseDown, .otherMouseDown]) { [weak self] _ in
      self?.outsideClick(at: NSEvent.mouseLocation)
    }
    observers.append(NotificationCenter.default.addObserver(forName: NSMenu.didBeginTrackingNotification, object:nil, queue:.main) { [weak self] _ in self?.menuTracking += 1 })
    observers.append(NotificationCenter.default.addObserver(forName: NSMenu.didEndTrackingNotification, object:nil, queue:.main) { [weak self] _ in
      if let self { self.menuTracking = max(0, self.menuTracking - 1) }
    })
    observers.append(NotificationCenter.default.addObserver(forName: NSApplication.didResignActiveNotification, object:nil, queue:.main) { [weak self] _ in
      DispatchQueue.main.asyncAfter(deadline:.now()+0.1) {
        guard let self, !self.closing, !NSApp.isActive else { return }
        self.outsideClick(at:NSEvent.mouseLocation)
      }
    })
    applyTheme()
    let loginLaunch =
      NSAppleEventManager.shared().currentAppleEvent?.paramDescriptor(forKeyword: keyAEPropData)?
      .enumCodeValue == keyAELaunchedAsLogInItem
    if !CommandLine.arguments.contains("--background") && !loginLaunch { show() }
    startBackend()
    startUpdates()
    observers.append(
      DistributedNotificationCenter.default().addObserver(
        forName: NSNotification.Name("io.github.herdr.Hud.show"), object: nil, queue: .main
      ) { [weak self] _ in self?.show() })
    #if DEBUG
      if CommandLine.arguments.contains("--smoke-test") { Task { await SmokeRun(self).run() } }
    #endif
    observers.append(
      DistributedNotificationCenter.default().addObserver(
        forName: NSNotification.Name("com.apple.screenIsLocked"), object: nil, queue: .main
      ) { [weak self] _ in self?.setDesktopActive(false) })
    observers.append(
      DistributedNotificationCenter.default().addObserver(
        forName: NSNotification.Name("com.apple.screenIsUnlocked"), object: nil, queue: .main
      ) { [weak self] _ in self?.setDesktopActive(true) })
    let center = NSWorkspace.shared.notificationCenter
    observers.append(
      center.addObserver(
        forName: NSWorkspace.sessionDidResignActiveNotification, object: nil, queue: .main
      ) { [weak self] _ in self?.setDesktopActive(false) })
    observers.append(
      center.addObserver(
        forName: NSWorkspace.sessionDidBecomeActiveNotification, object: nil, queue: .main
      ) { [weak self] _ in self?.setDesktopActive(true) })
    observers.append(
      center.addObserver(
        forName: NSWorkspace.screensDidSleepNotification, object: nil, queue: .main
      ) { [weak self] _ in self?.setDesktopActive(false) })
    observers.append(
      center.addObserver(forName: NSWorkspace.screensDidWakeNotification, object: nil, queue: .main)
      { [weak self] _ in self?.setDesktopActive(true) })
    observers.append(
      NotificationCenter.default.addObserver(
        forName: NSApplication.didChangeScreenParametersNotification, object: nil, queue: .main
      ) { [weak self] _ in self?.clampWindows() })
    observers.append(
      DistributedNotificationCenter.default().addObserver(
        forName: NSNotification.Name("AppleInterfaceThemeChangedNotification"), object: nil,
        queue: .main
      ) { [weak self] _ in self?.applyTheme() })
  }
  func installMenu() {
    let main = NSMenu()
    let app = NSMenu()
    let edit = NSMenu()
    let view = NSMenu()
    for (name, menu) in [("Herdr Hud", app), ("Edit", edit), ("View", view), ("Window", windowMenu)] {
      let item = NSMenuItem(title: name, action: nil, keyEquivalent: "")
      item.submenu = menu
      main.addItem(item)
    }
    windowMenu.delegate = self
    app.addItem(withTitle: "About Herdr Hud", action: #selector(about), keyEquivalent: "").target =
      self
    app.addItem(withTitle: "Settings…", action: #selector(settings), keyEquivalent: ",").target =
      self
    app.addItem(.separator())
    app.addItem(withTitle: "Hide Herdr Hud", action: #selector(hideHud), keyEquivalent: "h")
      .target = self
    app.addItem(withTitle: "Quit Herdr Hud", action: #selector(quit), keyEquivalent: "q").target =
      self
    for (name, action, key) in [
      ("Copy", #selector(NSText.copy(_:)), "c"), ("Paste", #selector(NSText.paste(_:)), "v"),
      ("Select All", #selector(NSText.selectAll(_:)), "a"),
    ] { edit.addItem(withTitle: name, action: action, keyEquivalent: key) }
    view.addItem(withTitle: "Search", action: #selector(focusSearch), keyEquivalent: "f").target =
      self
    view.addItem(withTitle: "Toggle Sidebar", action: #selector(toggleSidebar), keyEquivalent: "\\")
      .target = self
    view.addItem(withTitle: "Expand / Restore Hud", action: #selector(zoom), keyEquivalent: "")
      .target = self
    NSApp.mainMenu = main
  }
  func button(_ title:String,_ action:Selector,glyph:String) -> HudButton {
    let b = HudButton("",glyph:glyph,target:self,action:action)
    b.toolTip = title; b.setAccessibilityLabel(title); chromeButtons.append(b); return b
  }
  func buildWindow() {
    restoring = true
    window = NSWindow(contentRect:NSRect(x:0,y:0,width:1040,height:704),styleMask:[.titled,.closable,.resizable,.fullSizeContentView],backing:.buffered,defer:false)
    window.title = "Herdr Hud"; window.titleVisibility = .hidden; window.titlebarAppearsTransparent = true
    for type in [NSWindow.ButtonType.closeButton,.miniaturizeButton,.zoomButton] { window.standardWindowButton(type)?.isHidden = true }
    window.minSize = NSSize(width:620,height:360); window.delegate = self; window.isReleasedWhenClosed = false
    window.level = .floating; window.collectionBehavior = [.canJoinAllSpaces,.fullScreenAuxiliary]
    window.center(); window.setFrame(storedFrame(prefs.windowFrame,fallback:window.frame),display:false); normalFrame = window.frame
    let root = HudSurface(); window.contentView = root
    let credits = button("Credits",#selector(about),glyph:"info")
    let settings = button("Settings",#selector(self.settings),glyph:"settings")
    let hide = button("Hide Hud",#selector(hideHud),glyph:"minus")
    let expand = button("Expand / restore",#selector(zoom),glyph:"expand")
    themeButton = button("Switch light / dark",#selector(toggleTheme),glyph:"sun")
    let exit = button("Exit Hud — keep sessions running",#selector(quit),glyph:"power")
    updateButton = button("Download update", #selector(downloadUpdate), glyph:"down")
    updateButton.isHidden = true
    let left = NSStackView(views:[credits,settings]), trailing = NSStackView(views:[updateButton,hide,expand,themeButton,exit])
    for stack in [left,trailing] { stack.spacing = 6; stack.orientation = .horizontal }
    for button in chromeButtons { button.widthAnchor.constraint(equalToConstant:34).isActive = true; button.heightAnchor.constraint(equalToConstant:34).isActive = true }
    appTitle.font = HudStyle.font(14,bold:true); appTitle.alignment = .center
    appSubtitle.font = HudStyle.font(12); appSubtitle.alignment = .center
    for v in [left,trailing,appTitle,appSubtitle] { header.addSubview(v); v.translatesAutoresizingMaskIntoConstraints = false }
    NSLayoutConstraint.activate([
      left.leadingAnchor.constraint(equalTo:header.leadingAnchor,constant:6),left.centerYAnchor.constraint(equalTo:header.centerYAnchor),
      trailing.trailingAnchor.constraint(equalTo:header.trailingAnchor,constant:-6),trailing.centerYAnchor.constraint(equalTo:header.centerYAnchor),
      appTitle.centerXAnchor.constraint(equalTo:header.centerXAnchor),appTitle.topAnchor.constraint(equalTo:header.topAnchor,constant:8),
      appSubtitle.centerXAnchor.constraint(equalTo:header.centerXAnchor),appSubtitle.topAnchor.constraint(equalTo:appTitle.bottomAnchor,constant:1)
    ])
    search.placeholderString = "Find a terminal or agent…"; search.font = HudStyle.font(14); search.delegate = self; search.sendsSearchStringImmediately = true
    search.focusRingType = .none
    split.isVertical = true; split.dividerStyle = .thick; split.delegate = self
    sections.isVertical = false; sections.dividerStyle = .thick; sections.delegate = self
    emptyAgents.font = HudStyle.font(11); emptyAgents.alignment = .center
    sections.addArrangedSubview(section("SPACES",table:spaces,toggle:spaceToggle,action:#selector(toggleSpaces)))
    sections.addArrangedSubview(section("AGENTS",table:agents,toggle:agentToggle,action:#selector(toggleAgents),placeholder:emptyAgents))
    let create = HudButton("+  New space",target:self,action:#selector(newSpace)); create.setAccessibilityLabel("New space")
    sidebar = HudSidebar(search:search,sections:sections,create:create)
    sidebar.autoresizingMask = [.height]
    rightPane = HudTerminalPane(title:title,terminalHost:terminalHost); rightPane.autoresizingMask = [.width,.height]
    title.font = HudStyle.font(14); title.lineBreakMode = .byTruncatingTail
    split.addArrangedSubview(sidebar); split.addArrangedSubview(rightPane)
    status.font = HudStyle.font(11); status.lineBreakMode = .byTruncatingTail
    for view in [header,split,status] { view.translatesAutoresizingMaskIntoConstraints = false; root.addSubview(view) }
    NSLayoutConstraint.activate([
      header.topAnchor.constraint(equalTo:root.topAnchor),header.leadingAnchor.constraint(equalTo:root.leadingAnchor),header.trailingAnchor.constraint(equalTo:root.trailingAnchor),header.heightAnchor.constraint(equalToConstant:46),
      split.topAnchor.constraint(equalTo:header.bottomAnchor),split.leadingAnchor.constraint(equalTo:root.leadingAnchor,constant:4),split.trailingAnchor.constraint(equalTo:root.trailingAnchor),split.bottomAnchor.constraint(equalTo:status.topAnchor,constant:-6),
      status.leadingAnchor.constraint(equalTo:root.leadingAnchor,constant:14),status.trailingAnchor.constraint(equalTo:root.trailingAnchor,constant:-14),status.bottomAnchor.constraint(equalTo:root.bottomAnchor,constant:-7),status.heightAnchor.constraint(equalToConstant:16)
    ])
    sidebarToggle = button("Collapse sidebar",#selector(toggleSidebar),glyph:"left")
    sidebarToggle.frame = NSRect(x:0,y:0,width:24,height:26); root.addSubview(sidebarToggle)
    root.layoutSubtreeIfNeeded()
    split.setPosition(prefs.sidebarWidth == 0 ? 0 : max(245,prefs.sidebarWidth),ofDividerAt:0)
    sidebar.layoutSubtreeIfNeeded(); restoreSectionPosition()
    restoring = false; sidebarSaved = max(245,prefs.sidebarWidth); positionSidebarToggle()
  }
  func positionSidebarToggle() {
    guard let sidebar, let sidebarToggle, let root = window?.contentView else { return }
    sidebarToggle.frame = NSRect(x:max(0,split.frame.minX+sidebar.frame.width+split.dividerThickness/2-12),y:split.frame.maxY-30,width:24,height:26)
    sidebarToggle.glyph = sidebar.frame.width < 1 ? "right" : "left"
    sidebarToggle.toolTip = sidebar.frame.width < 1 ? "Expand sidebar" : "Collapse sidebar"
    root.addSubview(sidebarToggle,positioned:.above,relativeTo:split)
  }
  func section(_ name:String,table:SidebarTable,toggle:HudButton,action:Selector,placeholder:NSTextField? = nil) -> NSView {
    toggle.title = "⌄  " + name; toggle.target = self; toggle.action = action; toggle.showsBorder = false
    toggle.alignment = .left; toggle.font = HudStyle.font(10,bold:true)
    let col = NSTableColumn(identifier:NSUserInterfaceItemIdentifier("name")); col.width = 240; col.minWidth = 0; col.resizingMask = .autoresizingMask
    table.autoresizingMask = [.width]; table.columnAutoresizingStyle = .uniformColumnAutoresizingStyle
    table.addTableColumn(col); table.headerView = nil; table.rowHeight = 30; table.intercellSpacing = .zero; table.style = .plain; table.dataSource = self; table.delegate = self; table.allowsEmptySelection = true
    table.setAccessibilityLabel(name.capitalized); table.context = { [weak self,weak table] index in guard let self,let table else { return nil }; return self.contextMenu(table,index) }
    let scroll = NSScrollView(); scroll.documentView = table; scroll.hasVerticalScroller = true; scroll.autohidesScrollers = true; scroll.scrollerStyle = .overlay; scroll.drawsBackground = false
    return HudSection(heading:toggle,scroll:scroll,placeholder:placeholder)
  }
  func buildDesktop() {
    bubble = BubblePanel(
      contentRect: NSRect(x: 50, y: 100, width: 56, height: 56),
      styleMask: [.borderless, .nonactivatingPanel], backing: .buffered, defer: false)
    bubble.title = "Herdr Hud Floating H"
    bubble.isMovable = true
    bubble.worksWhenModal = true
    bubble.becomesKeyOnlyIfNeeded = true
    bubble.isFloatingPanel = true
    bubble.isOpaque = false
    bubble.backgroundColor = .clear
    bubble.hasShadow = true
    bubble.level = .statusBar
    bubble.hidesOnDeactivate = false
    bubble.collectionBehavior = [.canJoinAllSpaces, .fullScreenAuxiliary, .stationary]
    bubble.contentView = bubbleView
    var bubbleFrame = storedFrame(prefs.bubbleFrame, fallback: bubble.frame)
    bubbleFrame.size = NSSize(width:56,height:56)
    bubble.setFrame(clampedFrame(bubbleFrame,fallback:bubble.frame), display: false)
    bubbleView.toggle = { [weak self] in self?.toggle() }
    bubbleView.moved = { [weak self] in self?.save() }
    bubble.orderFrontRegardless()
    statusItem = NSStatusBar.system.statusItem(withLength: NSStatusItem.variableLength)
    statusItem.button?.title = "H"
    let menu = NSMenu()
    menu.addItem(withTitle: "Show / Hide Hud", action: #selector(toggle), keyEquivalent: "")
      .target = self
    menu.addItem(withTitle: "Settings…", action: #selector(settings), keyEquivalent: "").target =
      self
    menu.addItem(withTitle: "Launch at Login", action: #selector(toggleLogin), keyEquivalent: "")
      .target = self
    menu.addItem(.separator())
    menu.addItem(withTitle: "Quit Herdr Hud", action: #selector(quit), keyEquivalent: "").target =
      self
    statusItem.menu = menu
    updateLoginMenu()
  }
  func makeBackend() -> Backend {
    #if DEBUG
      if let name = ProcessInfo.processInfo.environment["HUD_TEST_SESSION"],
        name.hasPrefix("hud-mac-test-")
      {
        return Backend(path: prefs.herdrPath, defaultSession: name, isolated: true)
      }
    #endif
    return Backend(path: prefs.herdrPath)
  }
  func startBackend() {
    generation += 1
    let token = generation
    monitor?.stop()
    backend = makeBackend()
    let client = backend
    status.stringValue = "Connecting to Herdr…"
    worker.async { [weak self] in
      do {
        _ = try client.check()
        _ = try client.ensureDefault()
        DispatchQueue.main.async {
          guard let self, !self.closing, token == self.generation else { return }
          self.status.stringValue = "Drag to copy  ·  Shift+click CLI controls  ·  Right-click to paste"
          self.beginMonitoring(client, token: token)
        }
      } catch {
        DispatchQueue.main.async {
          guard let self, !self.closing, token == self.generation else { return }
          self.report(error)
          self.settings()
        }
      }
    }
  }
  func beginMonitoring(_ client: Backend, token: Int) {
    let monitor = Monitor(backend: client)
    self.monitor = monitor
    monitor.onSnapshot = { [weak self] session, snapshot in
      DispatchQueue.main.async {
        guard let self, !self.closing, token == self.generation else { return }
        self.received(session, snapshot)
      }
    }
    monitor.onSessions = { [weak self] sessions in
      DispatchQueue.main.async {
        guard let self, !self.closing, token == self.generation else { return }
        let live = Set(sessions.map(\.socket_path))
        self.snapshots = self.snapshots.filter { live.contains($0.key) }
        self.prune()
        self.render()
      }
    }
    monitor.onEvent = { [weak self] session, event in
      DispatchQueue.main.async {
        guard let self, !self.closing, token == self.generation else { return }
        self.event(session, event)
      }
    }
    monitor.onError = { [weak self] message in
      DispatchQueue.main.async {
        guard let self, !self.closing, token == self.generation else { return }
        self.status.stringValue = message
      }
    }
    monitor.onUnavailable = { [weak self] session, message in
      DispatchQueue.main.async {
        guard let self, !self.closing, token == self.generation else { return }
        self.disconnected.insert(session.socket_path)
        self.terminals.filter { $0.key.socket == session.socket_path }.values.forEach { $0.inputAvailable = false }
        self.spaces.reloadData(); self.agents.reloadData()
        self.status.stringValue = "Reconnecting to " + session.name + ": " + message
        self.render()
      }
    }
    monitor.start()
  }
  func received(_ session: Session, _ snapshot: Snapshot) {
    if disconnected.remove(session.socket_path) != nil {
      terminals.filter { $0.key.socket == session.socket_path }.values.forEach { $0.inputAvailable = true }
      spaces.reloadData(); agents.reloadData()
    }
    snapshots[session.socket_path] = (session, snapshot)
    for pane in snapshot.panes {
      let key = TerminalKey(session.socket_path, pane.terminal_id)
      if let identity = titleIdentity(pane.terminal_title_stripped) { terminalIdentities[key] = identity }
      if let message = attention(previous: previousStates[key], current: pane.agent_status) {
        markUnread(key, message: "\(snapshot.label(for:pane)): \(message)")
      }
      terminals[key]?.agentTerminal = pane.isAgent
      previousStates[key] = pane.agent_status
    }
    prune()
    render()
    if !showingSetup, let selected, let (activeSession, activeSnapshot, activePane) = pane(selected) {
      title.stringValue = terminalHeading(session: activeSession, snapshot: activeSnapshot, pane: activePane)
    }
    if selected == nil, let pane = snapshot.panes.first {
      select(TerminalKey(session.socket_path, pane.terminal_id))
    }
    if !normalized.contains(session.socket_path), let first = snapshot.workspaces.first {
      normalized.insert(session.socket_path)
      if session.name == backend.defaultSession && first.label == "~" {
        mutate {
          _ = try self.backend.request(
            session, "workspace.rename", ["workspace_id": first.workspace_id, "label": "Space 1"])
        }
      }
    }
  }
  func prune() {
    let live = Set(
      snapshots.flatMap { path, entry in entry.1.panes.map { TerminalKey(path, $0.terminal_id) } })
    for key in Array(terminals.keys) where !live.contains(key) {
      terminals.removeValue(forKey: key)?.detach()
    }
    terminalIdentities = terminalIdentities.filter { live.contains($0.key) }
    previousStates = previousStates.filter { live.contains($0.key) }
    unread.formIntersection(live)
    if let selected, !live.contains(selected) {
      self.selected = nil
      terminalHost.subviews.forEach { $0.removeFromSuperview() }
    }
    updateIndicators()
  }
  func pane(_ key: TerminalKey) -> (Session, Snapshot, Pane)? {
    guard let entry = snapshots[key.socket],
      let pane = entry.1.panes.first(where: { $0.terminal_id == key.id })
    else { return nil }
    return (entry.0, entry.1, pane)
  }
  func event(_ session: Session, _ event: [String: Any]) {
    guard event["event"] as? String == "pane.exited", let data = event["data"] as? [String: Any],
      let id = data["pane_id"] as? String,
      let p = snapshots[session.socket_path]?.1.panes.first(where: { $0.pane_id == id })
    else { return }
    markUnread(
      TerminalKey(session.socket_path, p.terminal_id), message: "\(p.displayName): Terminal exited")
    render()
  }
  func markUnread(_ key: TerminalKey, message: String) {
    if selected == key && window.isVisible && window.isKeyWindow { return }
    unread.insert(key)
    updateIndicators()
    status.stringValue = message
    guard desktopActive else { return }
    tooltipDismiss?.cancel()
    tooltip?.close()
    let popover = NSPopover()
    let controller = NSViewController()
    let label = NSTextField(wrappingLabelWithString: message)
    label.frame = NSRect(x: 12, y: 10, width: 245, height: 38)
    controller.view = NSView(frame: NSRect(x: 0, y: 0, width: 269, height: 58))
    controller.view.addSubview(label)
    popover.contentViewController = controller
    popover.behavior = .transient
    popover.show(relativeTo: bubbleView.bounds, of: bubbleView, preferredEdge: .maxX)
    tooltip = popover
    let work = DispatchWorkItem { [weak self] in self?.tooltip?.close() }
    tooltipDismiss = work
    DispatchQueue.main.asyncAfter(deadline: .now() + 5, execute: work)
  }
  func updateIndicators() {
    bubbleView.unread = unread.count
    statusItem?.button?.title = unread.isEmpty ? "H" : "H •"
    statusItem?.button?.toolTip = "Herdr Hud · \(unread.count) unread terminals"
  }
  func acknowledged() {
    if let selected {
      unread.remove(selected)
      updateIndicators()
      render()
    }
  }
  func select(_ key: TerminalKey) {
    guard !disconnected.contains(key.socket), let (session, snapshot, pane) = pane(key) else { return }
    leaveSetup()
    selected = key
    workspaceSelection[SpaceKey(key.socket, pane.workspace_id)] = key
    let terminal: HudTerminal
    if let existing = terminals[key] {
      terminal = existing
    } else {
      terminal = HudTerminal()
      terminals[key] = terminal
      if let colors = currentColors { terminal.apply(colors) }
    }
    if terminal.superview !== terminalHost {
      terminalHost.subviews.forEach { $0.removeFromSuperview() }
      terminal.frame = terminalHost.bounds
      terminal.autoresizingMask = [.width, .height]
      terminalHost.addSubview(terminal)
    }
    terminal.agentTerminal = !(pane.agent ?? "").isEmpty
    terminal.onSelectionStatus = { [weak self] message in self?.status.stringValue = message }
    terminal.readHistory = { [weak self] completion in
      guard let self, !self.closing else { return }
      self.worker.async { [weak self] in
        guard let self, !self.closing else { return }
        let result = Result<String, Error> {
          let reply = try self.backend.request(session, "pane.read", [
            "pane_id": pane.pane_id, "source": "recent", "lines": 20000,
            "format": "ansi", "strip_ansi": false])
          guard let read = reply["read"] as? [String: Any], let text = read["text"] as? String else {
            throw HudError.message("Invalid history response")
          }
          return text
        }
        DispatchQueue.main.async { [weak self] in
          guard let self, !self.closing else { return }
          completion(result)
        }
      }
    }
    if !terminal.connected {
      do {
        terminal.attach(executable: try backend.executable(), session: session, pane: pane)
      } catch { report(error) }
    }
    title.stringValue = terminalHeading(session:session,snapshot:snapshot,pane:pane)
    acknowledged()
    DispatchQueue.main.async { [weak self, weak terminal] in
      guard let self, self.selected == key, let terminal else { return }
      self.window.makeFirstResponder(terminal)
    }
  }
  func paneTitle(_ pane:Pane, snapshot:Snapshot) -> String {
    let tab = pane.tab_label ?? snapshot.tabs.first { $0.tab_id == pane.tab_id }?.label ?? ""
    return [pane.label,pane.agent,tab.isEmpty || Int(tab) != nil ? nil : tab,pane.title]
      .compactMap { $0 }.first { !$0.isEmpty } ?? (tab.isEmpty ? "Terminal" : "Terminal " + tab)
  }
  func sidebarTitle(_ pane:Pane, snapshot:Snapshot) -> String {
    guard let agent = pane.agent, !agent.isEmpty else { return paneTitle(pane,snapshot:snapshot) }
    let members = snapshot.panes.filter { $0.workspace_id == pane.workspace_id }
    let number = (members.firstIndex { $0.terminal_id == pane.terminal_id } ?? 0) + 1
    let name = [pane.tab_label,pane.label].compactMap { $0 }.first { !$0.isEmpty } ?? ""
    let terminalName = name.isEmpty || Int(name) != nil || name.lowercased() == agent.lowercased() ? "Terminal \(number)" : name
    return "\(agent) · \(terminalName)"
  }
  func userHost(_ session: Session, _ pane: Pane) -> String {
    titleIdentity(pane.terminal_title_stripped)
      ?? terminalIdentities[TerminalKey(session.socket_path, pane.terminal_id)]
      ?? session.remoteTarget ?? (NSUserName() + "@" + (Foundation.Host.current().localizedName ?? ProcessInfo.processInfo.hostName))
  }
  func terminalHeading(session:Session,snapshot:Snapshot,pane:Pane) -> String {
    let space = snapshot.workspaces.first { $0.workspace_id == pane.workspace_id }?.label ?? session.name
    let identity = titleIdentity(pane.terminal_title_stripped) ?? (pane.isAgent ? userHost(session, pane) : nil)
    return (session.name == backend.defaultSession ? "" : session.name + " / ") + space + "  /  " + paneTitle(pane,snapshot:snapshot) + (identity.map { " - " + $0 } ?? "")
  }
  func render() {
    guard !closing else { return }
    let query = search.stringValue.trimmingCharacters(in: .whitespacesAndNewlines).lowercased()
    var nextSpaces: [Row] = []
    var nextAgents: [Row] = []
    for (_, entry) in snapshots.sorted(by: { $0.value.0.name < $1.value.0.name }) {
      let (session, snapshot) = entry
      let box = SessionBox(session)
      for space in snapshot.workspaces {
        let members = snapshot.panes.filter { $0.workspace_id == space.workspace_id }
        let matching = members.filter { p in
          query.isEmpty
            || [sidebarTitle(p,snapshot:snapshot), paneTitle(p,snapshot:snapshot), p.agent ?? "", p.title ?? "", p.process_title ?? ""]
              .contains { $0.lowercased().contains(query) }
        }
        guard !matching.isEmpty else { continue }
        let key = SpaceKey(session.socket_path, space.workspace_id)
        let closed = collapsed.contains(key)
        let spaceName =
          (session.name == backend.defaultSession ? "" : session.name + " / ")
          + (space.label ?? "Space")
        let groupState =
          members.contains { unread.contains(TerminalKey(session.socket_path, $0.terminal_id)) }
          ? "unread" : members.contains { $0.agent_status == "working" } ? "working" : "idle"
        nextSpaces.append(
          Row(
            session: box, workspace: space.workspace_id, terminal: nil, title: spaceName,
            status: groupState, collapsed: closed))
        for p in matching {
          let key = TerminalKey(session.socket_path, p.terminal_id)
          let state =
            p.agent_status == "working" ? "working" : unread.contains(key) ? "unread" : "idle"
          if !closed || !query.isEmpty {
            nextSpaces.append(
              Row(
                session: box, workspace: space.workspace_id, terminal: p.terminal_id,
                title: sidebarTitle(p,snapshot:snapshot), status: state))
          }
          if p.isAgent {
            let activity = p.agent_status == "blocked" ? "Needs input" : p.agent_status == "done" ? "Finished" : p.agent_status.capitalized
            nextAgents.append(
              Row(
                session: box, workspace: space.workspace_id, terminal: p.terminal_id,
                title: sidebarTitle(p,snapshot:snapshot), status: state, subtitle: "\(p.agent!) · \(activity) · \(spaceName)"))
          }
        }
      }
    }
    if !prefs.spacesExpanded { nextSpaces = [] }
    if !prefs.agentsExpanded { nextAgents = [] }
    emptyAgents.isHidden = !prefs.agentsExpanded || !nextAgents.isEmpty
    spaceToggle.title = (prefs.spacesExpanded ? "⌄  " : "›  ") + "SPACES"
    agentToggle.title = (prefs.agentsExpanded ? "⌄  " : "›  ") + "AGENTS"
    let signature: ([Row]) -> [String] = {
      $0.map { $0.identity + $0.title + $0.subtitle + $0.status + String($0.collapsed) }
    }
    rebuilding = true
    if signature(nextSpaces) != signature(spaceRows) {
      spaceRows = nextSpaces
      spaces.reloadData()
    }
    if signature(nextAgents) != signature(agentRows) {
      agentRows = nextAgents
      agents.reloadData()
    }
    for (table, rows) in [(spaces, spaceRows), (agents, agentRows)] {
      if let selected,
        let i = rows.firstIndex(where: {
          $0.terminal == selected.id && $0.session.value.socket_path == selected.socket
        })
      {
        table.selectRowIndexes(IndexSet(integer: i), byExtendingSelection: false)
      } else {
        table.deselectAll(nil)
      }
    }
    rebuilding = false
  }
  func numberOfRows(in tableView: NSTableView) -> Int {
    tableView === spaces ? spaceRows.count : agentRows.count
  }
  func tableView(_ tableView: NSTableView, viewFor tableColumn: NSTableColumn?, row: Int) -> NSView?
  {
    let rows = tableView === spaces ? spaceRows : agentRows
    guard rows.indices.contains(row) else { return nil }
    let item = rows[row]
    let id = NSUserInterfaceItemIdentifier("row")
    let cell =
      tableView.makeView(withIdentifier: id, owner: self) as? SidebarCell
      ?? SidebarCell(frame: .zero)
    cell.identifier = id
    cell.alphaValue = disconnected.contains(item.session.value.socket_path) ? 0.5 : 1
    cell.label.textColor = currentColors.map { NSColor(hex: $0.foreground) } ?? .labelColor
    cell.label.stringValue = item.title
    cell.toolTip = nil
    cell.identityText = item.terminal.flatMap { pane(TerminalKey(item.session.value.socket_path, $0)) }.map { userHost($0.0, $0.2) }
    cell.label.font = HudStyle.font(item.terminal == nil ? 12 : 14, bold:item.terminal == nil)
    cell.group = item.terminal == nil; cell.agentShortcut = tableView === agents
    cell.subtitle.stringValue = item.subtitle; cell.subtitle.textColor = HudStyle.foreground.withAlphaComponent(0.7)
    cell.actions = { [weak self,weak cell] in guard let self,let cell,let menu = self.contextMenu(tableView,row) else { return }; menu.popUp(positioning:nil,at:NSPoint(x:0,y:cell.bounds.height),in:cell) }
    cell.needsLayout = true; cell.needsDisplay = true
    cell.disclosure.isHidden = item.terminal != nil
    cell.disclosure.glyph = item.collapsed ? "right" : "down"
    cell.plus.isHidden = item.terminal != nil
    cell.dot.stringValue = item.status == "idle" ? "○" : "●"
    cell.dot.textColor =
      item.status == "working"
      ? NSColor(hex:HudStyle.dark ? "#8bd17c" : "#287a27") : item.status == "unread" ? NSColor(hex:HudStyle.dark ? "#f6d365" : "#b58100") : HudStyle.foreground
    cell.expand = { [weak self] in
      guard let self else { return }
      let key = SpaceKey(item.session.value.socket_path, item.workspace)
      if self.collapsed.contains(key) {
        self.collapsed.remove(key)
      } else {
        self.collapsed.insert(key)
      }
      DispatchQueue.main.async { self.render() }
    }
    cell.add = { [weak self] in self?.newTerminal(item) }
    return cell
  }
  func tableView(_ tableView:NSTableView,heightOfRow row:Int) -> CGFloat {
    let rows = tableView === spaces ? spaceRows : agentRows
    guard rows.indices.contains(row) else { return 30 }
    return rows[row].terminal == nil ? 40 : tableView === agents ? 48 : 30
  }
  func tableView(_ tableView:NSTableView,rowViewForRow row:Int) -> NSTableRowView? {
    let view = HudRowView(); let rows = tableView === spaces ? spaceRows : agentRows
    view.inset = tableView === spaces && rows.indices.contains(row) && rows[row].terminal != nil ? 18 : 0
    return view
  }
  func tableViewSelectionDidChange(_ notification: Notification) {
    guard !rebuilding, let table = notification.object as? NSTableView else { return }
    let rows = table === spaces ? spaceRows : agentRows
    let index = table.selectedRow
    guard rows.indices.contains(index) else { return }
    let item = rows[index]
    let path = item.session.value.socket_path
    if let terminal = item.terminal {
      select(TerminalKey(path, terminal))
    } else {
      let space = SpaceKey(path, item.workspace)
      if let previous = workspaceSelection[space], pane(previous) != nil {
        select(previous)
      } else if let p = snapshots[path]?.1.panes.first(where: { $0.workspace_id == item.workspace })
      {
        select(TerminalKey(path, p.terminal_id))
      }
    }
  }
  func controlTextDidChange(_ obj: Notification) { render() }
  func contextMenu(_ table: NSTableView, _ index: Int) -> NSMenu? {
    let rows = table === spaces ? spaceRows : agentRows
    guard rows.indices.contains(index) else { return nil }
    let row = rows[index]
    guard !disconnected.contains(row.session.value.socket_path) else { return nil }
    let menu = NSMenu()
    for (name, action) in [
      ("Rename…", #selector(renameRow(_:))), ("Close", #selector(closeRow(_:))),
    ] {
      if name == "Close" && !canClose(row) { continue }
      let item = menu.addItem(withTitle: name, action: action, keyEquivalent: "")
      item.target = self
      item.representedObject = row
    }
    return menu
  }
  func canClose(_ row: Row) -> Bool {
    guard let snap = snapshots[row.session.value.socket_path]?.1 else { return false }
    if let id = row.terminal, let p = snap.panes.first(where: { $0.terminal_id == id }) {
      return snap.canClose(pane: p)
    }
    return snap.workspaces.contains { $0.workspace_id == row.workspace }
      && snap.workspaces.first?.workspace_id != row.workspace
  }
  func prompt(_ message: String, initial: String, accept: String) -> String? {
    let alert = NSAlert()
    alert.messageText = message
    alert.addButton(withTitle: accept)
    alert.addButton(withTitle: "Cancel")
    let field = NSTextField(string: initial)
    field.frame = NSRect(x: 0, y: 0, width: 300, height: 26)
    alert.accessoryView = field
    alert.window.initialFirstResponder = field
    guard alert.runModal() == .alertFirstButtonReturn else { return nil }
    let value = field.stringValue.trimmingCharacters(in: .whitespacesAndNewlines)
    return value.isEmpty ? nil : value
  }
  @objc func renameRow(_ sender: NSMenuItem) {
    guard let row = sender.representedObject as? Row else { return }
    let initialName =
      row.terminal == nil
      ? snapshots[row.session.value.socket_path]?.1.workspaces.first(where: {
        $0.workspace_id == row.workspace
      })?.label ?? row.title : row.title
    guard
      let name = prompt(
        row.terminal == nil ? "Rename space" : "Rename terminal", initial: initialName,
        accept: "Rename")
    else { return }
    let session = row.session.value
    if let id = row.terminal, let (_, _, pane) = pane(TerminalKey(session.socket_path, id)) {
      mutate {
        _ = try self.backend.request(
          session, "pane.rename", ["pane_id": pane.pane_id, "label": name])
        _ = try self.backend.request(session, "tab.rename", ["tab_id": pane.tab_id, "label": name])
      }
    } else {
      mutate {
        _ = try self.backend.request(
          session, "workspace.rename", ["workspace_id": row.workspace, "label": name])
      }
    }
  }
  @objc func closeRow(_ sender: NSMenuItem) {
    guard let row = sender.representedObject as? Row, canClose(row) else { return }
    let session = row.session.value
    if let id = row.terminal, let (_, _, p) = pane(TerminalKey(session.socket_path, id)) {
      if p.isAgent {
        let a = NSAlert()
        a.messageText = "Close terminal and stop agent?"
        a.informativeText = "This stops the agent and other processes in this terminal."
        a.addButton(withTitle: "Cancel")
        a.addButton(withTitle: "Close terminal and stop agent")
        guard a.runModal() == .alertSecondButtonReturn else { return }
      }
      guard canClose(row) else { return }
      mutate { _ = try self.backend.request(session, "pane.close", ["pane_id": p.pane_id]) }
    } else {
      mutate {
        _ = try self.backend.request(session, "workspace.close", ["workspace_id": row.workspace])
      }
    }
  }
  func mutate(_ operation: @escaping () throws -> Void, completion: (() -> Void)? = nil) {
    guard !busy else {
      status.stringValue = "Please wait for the current Herdr action to finish."
      return
    }
    busy = true
    worker.async { [weak self] in
      do {
        try operation()
        DispatchQueue.main.async {
          guard let self, !self.closing else { return }
          self.busy = false
          completion?()
        }
        self?.refresh()
      } catch {
        DispatchQueue.main.async {
          guard let self, !self.closing else { return }
          self.busy = false
          self.report(error)
        }
      }
    }
  }
  func refresh() {
    let client = backend
    if let sessions = try? client.sessions() {
      for session in sessions {
        if let snap = try? client.snapshot(session) {
          DispatchQueue.main.async { [weak self] in
            guard let self, !self.closing else { return }
            self.received(session, snap)
          }
        }
      }
    }
  }
  @objc func toggleAutoHide(_ sender: NSButton) {
    prefs.autoHide = sender.state == .on
    save()
  }
  @objc func newSpace() {
    let labels = snapshots.values.flatMap { $0.1.workspaces.compactMap(\.label) }
    var n = 1
    while labels.contains("Space \(n)") { n += 1 }
    let dialog = NSAlert()
    dialog.messageText = "New space"
    dialog.addButton(withTitle: "Create"); dialog.addButton(withTitle: "Cancel")
    let form = NSStackView(); form.orientation = .vertical; form.alignment = .leading
    let label = NSTextField(string: "Space \(n)")
    let enabled = NSButton(checkboxWithTitle: "Start an agent in this space", target: nil, action: nil)
    let kind = NSPopUpButton(); kind.addItems(withTitles: ["pi", "claude", "codex", "gemini", "cursor", "devin", "agy", "cline", "omp", "mastracode", "opencode", "copilot", "kimi", "kiro", "droid", "amp", "grok", "hermes", "kilo", "qodercli", "qwen", "letta", "maki", "muse"]); kind.selectItem(withTitle: "codex")
    let agent = NSTextField(string: "agent-\(n)")
    label.placeholderString = "Space name"; agent.placeholderString = "Agent name"
    for view in [label, enabled, kind, agent] as [NSView] { form.addArrangedSubview(view) }
    form.frame = NSRect(x: 0, y: 0, width: 320, height: 130)
    dialog.accessoryView = form
    guard dialog.runModal() == .alertFirstButtonReturn else { return }
    let name = label.stringValue.trimmingCharacters(in: .whitespacesAndNewlines)
    let agentName = agent.stringValue.trimmingCharacters(in: .whitespacesAndNewlines)
    guard !name.isEmpty, enabled.state != .on || agentName.range(of: "^[a-z][a-z0-9_-]{0,31}$", options: .regularExpression) != nil else {
      status.stringValue = "Enter a space name and a valid lowercase agent name."; return
    }
    let agentKind = enabled.state == .on ? kind.titleOfSelectedItem : nil
    mutate {
      let session = try self.backend.ensureDefault(initialize: false)
      let result = try self.backend.request(
        session, "workspace.create", ["label": name, "cwd": NSHomeDirectory(), "focus": false])
      self.selectCreated(session, result)
      if let kind = agentKind, let pane = result["root_pane"] as? [String: Any], let id = pane["pane_id"] as? String {
        _ = try Host.run(self.backend.executable(), ["--session", self.backend.defaultSession,
          "agent", "start", agentName, "--kind", kind, "--pane", id, "--timeout", "30000"], timeout: 40)
      }
    }
  }
  func newTerminal(_ row: Row) {
    let session = row.session.value
    guard !disconnected.contains(session.socket_path) else { return }
    guard let snapshot = snapshots[session.socket_path]?.1 else { return }
    let members = snapshot.panes.filter { $0.workspace_id == row.workspace }
    let source =
      selected.flatMap { pane($0)?.2 }.flatMap {
        $0.workspace_id == row.workspace && selected?.socket == session.socket_path ? $0 : nil
      } ?? members.first
    let labels = members.map { snapshot.label(for: $0) }
    var n = members.count + 1
    while labels.contains("Terminal \(n)") { n += 1 }
    let cwd = session.terminalDirectory(foreground: source?.foreground_cwd,
      cwd: source?.cwd, localHome: NSHomeDirectory())
    mutate {
      var params: [String: Any] = ["workspace_id": row.workspace,
        "label": "Terminal \(n)", "focus": false]
      if let cwd { params["cwd"] = cwd }
      let result = try self.backend.request(
        session, "tab.create", params)
      self.selectCreated(session, result)
    }
  }
  func selectCreated(_ session: Session, _ result: [String: Any]) {
    guard let pane = result["root_pane"] as? [String: Any], let id = pane["terminal_id"] as? String,
      let snapshot = try? backend.snapshot(session)
    else { return }
    DispatchQueue.main.async { [weak self] in
      guard let self, !self.closing else { return }
      if let space = pane["workspace_id"] as? String {
        self.collapsed.remove(SpaceKey(session.socket_path, space))
      }
      self.received(session, snapshot)
      self.select(TerminalKey(session.socket_path, id))
    }
  }
  var currentColors: PaletteVariant? {
    let dark = window?.effectiveAppearance.bestMatch(from: [.darkAqua, .aqua]) == .darkAqua
    let p = palettes[prefs.palette] ?? palettes["Vs Code"]
    return dark ? p?.dark : p?.light
  }
  func applyTheme() {
    let appearance: NSAppearance? =
      prefs.appearance == "system"
      ? nil : NSAppearance(named: prefs.appearance == "dark" ? .darkAqua : .aqua)
    window?.appearance = appearance
    bubble?.appearance = appearance
    settingsController?.window?.appearance = appearance
    guard let colors = currentColors else { return }
    HudStyle.apply(colors,dark:window.effectiveAppearance.bestMatch(from:[.darkAqua,.aqua]) == .darkAqua)
    window.backgroundColor = HudStyle.background
    (window.contentView as? HudSurface)?.fill = HudStyle.background
    header.fill = HudStyle.side; header.border = HudStyle.line
    sidebar.fill = HudStyle.side; rightPane.fill = HudStyle.background
    emptyAgents.textColor = HudStyle.foreground.withAlphaComponent(0.7)
    for case let section as HudSection in sections.subviews { section.fill = HudStyle.side }
    terminalHost.wantsLayer = true; terminalHost.layer?.backgroundColor = HudStyle.background.cgColor
    for table in [spaces,agents] { table.backgroundColor = HudStyle.background }
    title.textColor = HudStyle.foreground; appTitle.textColor = HudStyle.foreground
    appSubtitle.textColor = HudStyle.foreground.withAlphaComponent(0.7)
    status.textColor = HudStyle.foreground.withAlphaComponent(0.7)
    search.textColor = HudStyle.foreground; search.backgroundColor = HudStyle.side
    search.placeholderAttributedString = NSAttributedString(string:"Find a terminal or agent…",attributes:[.font:HudStyle.font(14),.foregroundColor:HudStyle.foreground.withAlphaComponent(0.5)])
    themeButton.glyph = HudStyle.dark ? "sun" : "moon"
    chromeButtons.forEach { $0.needsDisplay = true }; sidebar.create.needsDisplay = true
    spaceToggle.needsDisplay = true; agentToggle.needsDisplay = true
    split.needsDisplay = true; sections.needsDisplay = true
    terminals.values.forEach { $0.apply(colors) }
    let wasRebuilding = rebuilding
    rebuilding = true
    spaces.reloadData(); agents.reloadData()
    rebuilding = wasRebuilding
    if !wasRebuilding { render() }
    bubbleView.needsDisplay = true
    setupPanel?.refresh(); settingsController?.syncAppearance()
    save()
  }
  func report(_ error: Error) {
    status.stringValue = error.localizedDescription
    NSLog("Herdr Hud: %@", error.localizedDescription)
  }
  @objc func show() {
    window.makeKeyAndOrderFront(nil)
    NSApp.activate(ignoringOtherApps: true)
    acknowledged()
    if !showingSetup, let selected, let term = terminals[selected] { window.makeFirstResponder(term) }
  }
  @objc func hideHud() {
    terminals.values.forEach { $0.endHistorySelection() }
    save()
    window.orderOut(nil)
  }
  func outsideClick(at point: NSPoint) {
    guard prefs.autoHide, !bubbleView.isInteracting, menuTracking == 0, !showingSetup, window.isVisible, !bubble.frame.contains(point),
      NSApp.modalWindow == nil, window.attachedSheet == nil,
      settingsController?.window?.isVisible != true, !window.inLiveResize else { return }
    hideHud()
  }
  @objc func toggle() { if window.isVisible { hideHud() } else { show() } }
  @objc func quit() { NSApp.terminate(nil) }
  @objc func zoom() {
    if !window.isZoomed { normalFrame = window.frame }
    window.zoom(nil)
    save()
    restoreTerminalFocus()
  }
  @objc func focusSearch() {
    show()
    window.makeFirstResponder(search)
  }
  @objc func toggleSidebar() {
    let width = sidebar.frame.width
    if width > 30 {
      sidebarSaved = width
      split.setPosition(0, ofDividerAt: 0)
    } else {
      split.setPosition(sidebarSaved, ofDividerAt: 0)
    }
    save()
    restoreTerminalFocus()
  }
  func restoreSectionPosition() {
    guard !restoringSections else { return }
    restoringSections = true
    let maximum = max(32,sections.bounds.height-38)
    let position = !prefs.spacesExpanded ? 32 : !prefs.agentsExpanded ? maximum : min(maximum,prefs.sectionPosition)
    sections.setPosition(position,ofDividerAt:0)
    restoringSections = false
  }
  @objc func toggleSpaces() {
    prefs.spacesExpanded.toggle(); restoreSectionPosition(); render(); save(); restoreTerminalFocus()
  }
  @objc func toggleAgents() {
    prefs.agentsExpanded.toggle(); restoreSectionPosition(); render(); save(); restoreTerminalFocus()
  }
  @objc func toggleTheme() {
    prefs.appearance =
      window.effectiveAppearance.bestMatch(from: [.darkAqua, .aqua]) == .darkAqua ? "light" : "dark"
    applyTheme()
    restoreTerminalFocus()
  }
  func restoreTerminalFocus() {
    DispatchQueue.main.async { [weak self] in
      guard let self, !self.closing, !self.showingSetup, self.window.isKeyWindow,
        self.window.attachedSheet == nil, let key = self.selected, let terminal = self.terminals[key]
      else { return }
      self.window.makeFirstResponder(terminal)
    }
  }
  @objc func settings() {
    showingSetup = true
    if setupPanel == nil { setupPanel = HudSetupPanel(app:self) }
    if let panel = setupPanel { rightPane.setup = panel; rightPane.addSubview(panel); panel.isHidden = false; panel.refresh() }
    terminalHost.isHidden = true; title.stringValue = "Settings"; rightPane.needsLayout = true; show()
  }
  @objc func chooseTheme() {
    if settingsController == nil { settingsController = SettingsController(app:self) }
    settingsController?.syncAppearance(); settingsController?.showWindow(nil); settingsController?.window?.makeKeyAndOrderFront(nil)
  }
  @objc func leaveSetup() {
    showingSetup = false; setupPanel?.isHidden = true; terminalHost.isHidden = false
    if let selected,let (session,snapshot,pane) = pane(selected) { title.stringValue = terminalHeading(session:session,snapshot:snapshot,pane:pane) }
  }
  @objc func about() {
    NSApp.orderFrontStandardAboutPanel(options: [
      .applicationName: "Herdr Hud", .applicationVersion: "1.5 · macOS",
      .credits: NSAttributedString(
        string:
          "Native macOS port of Alex Jax’s independent Ubuntu remix.\nOriginal Herdr HUD: Alex Finn.\nPalettes: Christian Hergert / Ptyxis. Terminal: SwiftTerm contributors.\nIcons: GNOME Project. Interface font: DejaVu.\nGPL-3.0-or-later; third-party notices are bundled."
      ),
    ])
  }
  @objc func toggleLogin() {
    do {
      if SMAppService.mainApp.status == .enabled {
        try SMAppService.mainApp.unregister()
      } else {
        try SMAppService.mainApp.register()
      }
      updateLoginMenu()
    } catch {
      report(error)
      let alert = NSAlert(error: error)
      alert.runModal()
    }
  }
  func updateLoginMenu() {
    statusItem.menu?.items.first(where: { $0.title == "Launch at Login" })?.state =
      SMAppService.mainApp.status == .enabled ? .on : .off
  }
  func setDesktopActive(_ active: Bool) {
    desktopActive = active
    if active {
      bubble.orderFrontRegardless()
    } else {
      bubbleView.cancelDrag()
      bubble.orderOut(nil)
      tooltip?.close()
    }
  }
  func clampWindows() {
    window.setFrame(clampedFrame(window.frame, fallback: window.frame), display: true)
    bubble.setFrame(clampedFrame(bubble.frame, fallback: bubble.frame), display: true)
    save()
  }
  func save() {
    guard window != nil, bubble != nil, !restoring else { return }
    prefs.windowFrame = frameArray(window.isZoomed ? normalFrame : window.frame)
    prefs.bubbleFrame = frameArray(bubble.frame)
    prefs.sidebarWidth = sidebar.frame.width
    if prefs.spacesExpanded && prefs.agentsExpanded && !restoringSections {
      prefs.sectionPosition = Double(sections.subviews.first?.frame.height ?? 260)
    }
    do { try prefs.save() } catch {
      NSLog("Cannot save Hud settings: %@", error.localizedDescription)
    }
  }
  func windowShouldClose(_ sender: NSWindow) -> Bool {
    hideHud()
    return false
  }
  func windowDidBecomeKey(_ notification: Notification) { acknowledged() }
  func windowDidMove(_ notification: Notification) {
    if !window.isZoomed { normalFrame = window.frame }
    save()
  }
  func windowDidEndLiveResize(_ notification: Notification) {
    if !window.isZoomed { normalFrame = window.frame }
    save()
  }
  func splitViewDidResizeSubviews(_ notification: Notification) {
    positionSidebarToggle()
    if !restoring, !restoringSections, !prefs.spacesExpanded || !prefs.agentsExpanded { restoreSectionPosition() }
    save()
  }
  func splitView(_ splitView: NSSplitView, canCollapseSubview subview: NSView) -> Bool {
    splitView === split
  }
  func splitView(_ splitView: NSSplitView, shouldAdjustSizeOfSubview view: NSView) -> Bool {
    splitView !== split || view !== sidebar
  }
  func applicationShouldTerminateAfterLastWindowClosed(_ sender: NSApplication) -> Bool { false }
  func applicationShouldHandleReopen(_ sender: NSApplication, hasVisibleWindows flag: Bool) -> Bool
  {
    show()
    return false
  }
  func applicationWillTerminate(_ notification: Notification) {
    closing = true
    updateTimer?.invalidate()
    if let outsideClickMonitor { NSEvent.removeMonitor(outsideClickMonitor) }
    save()
    monitor?.stop()
    terminals.values.forEach { $0.detach() }
    bubble?.orderOut(nil)
    tooltip?.close()
    statusItem.map { NSStatusBar.system.removeStatusItem($0) }
  }
}
