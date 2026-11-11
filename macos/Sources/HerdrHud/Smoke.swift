#if DEBUG
  import AppKit
  import HudCore

  @MainActor
  final class SmokeRun {
    unowned let app: HudApp
    init(_ app: HudApp) { self.app = app }
    func require(_ condition: @autoclosure () -> Bool, _ message: String) throws {
      if !condition() { throw HudError.message("SMOKE: " + message) }
    }
    func until(_ message: String, timeout: TimeInterval = 12, _ predicate: () -> Bool) async throws
    {
      let deadline = Date().addingTimeInterval(timeout)
      while !predicate() {
        if Date() > deadline {
          throw HudError.message("SMOKE timed out: " + message + "; " + app.status.stringValue)
        }
        try await Task.sleep(nanoseconds: 100_000_000)
      }
    }
    func rpc(_ session: Session, _ method: String, _ params: [String: Any] = [:]) async throws
      -> [String: Any]
    {
      let backend = app.backend
      return try await withCheckedThrowingContinuation { continuation in
        app.worker.async {
          do { continuation.resume(returning: try backend.request(session, method, params)) } catch
          { continuation.resume(throwing: error) }
        }
      }
    }
    func snap(_ session: Session) async throws -> Snapshot {
      let backend = app.backend
      return try await withCheckedThrowingContinuation { continuation in
        app.worker.async {
          do { continuation.resume(returning: try backend.snapshot(session)) } catch {
            continuation.resume(throwing: error)
          }
        }
      }
    }
    func run() async {
      let savedClipboard = (NSPasteboard.general.pasteboardItems ?? []).map { item in
        item.types.compactMap { type in item.data(forType: type).map { (type, $0) } }
      }
      var result = ""
      var successful = false
      try? "RUNNING".write(
        toFile: "/private/tmp/herdr-hud-smoke-result.txt", atomically: true, encoding: .utf8)
      do {
        try await until("initial terminal") {
          app.selected != nil && app.selected.flatMap { app.terminals[$0]?.connected } == true
        }
        guard let key = app.selected, let (session, initial, pane) = app.pane(key),
          let terminal = app.terminals[key]
        else { throw HudError.message("Missing initial session") }
        try require(session.name.hasPrefix("hud-mac-test-"), "disposable session isolation")
        try require(
          initial.workspaces.count == 1 && initial.panes.count == 1, "one initial workspace")
        try require(!initial.canClose(pane: pane), "first terminal protected")
        terminal.send(source: terminal, data: Array("printf '\\033]0;root@remote:/app\\007'; sleep 20\r".utf8)[...])
        try await until("reported terminal identity", timeout: 20) { app.title.stringValue.hasSuffix(" - root@remote") }
        terminal.send(source: terminal, data: [3][...])
        try await Task.sleep(nanoseconds: 300_000_000)
        terminal.send(source: terminal, data: Array("printf '\\033]0;Codex\\007'; sleep 20\r".utf8)[...])
        try await until("cleared terminal identity", timeout: 20) { !app.title.stringValue.contains("root@remote") }
        terminal.send(source: terminal, data: [3][...])
        try await Task.sleep(nanoseconds: 300_000_000)
        try await interactionChecks()
        try await liveCLIChecks()
        let screen = {
          terminal.terminalStateSnapshot().visibleRows.map(\.text).joined(separator: "\n")
        }
        terminal.send(
          source: terminal, data: Array("printf '\\110\\125\\104_MAC_OK\\n'\r".utf8)[...])
        try await until("terminal output") { screen().contains("HUD_MAC_OK") }
        terminal.selectAll()
        terminal.copy(terminal)
        try require(
          NSPasteboard.general.string(forType: .string)?.contains("HUD_MAC_OK") == true,
          "clipboard copy")
        NSPasteboard.general.clearContents()
        NSPasteboard.general.setString("printf '\\110\\125\\104_PASTE_OK\\n'", forType: .string)
        terminal.paste(terminal)
        try await Task.sleep(nanoseconds: 200_000_000)
        terminal.send(source: terminal, data: [13][...])
        try await until("clipboard paste") { screen().contains("HUD_PASTE_OK") }
        try require(!terminal.selectionActive, "paste clears selection")
        app.window.setContentSize(NSSize(width: 1100, height: 720))
        try await Task.sleep(nanoseconds: 300_000_000)
        terminal.send(source: terminal, data: Array("stty size\r".utf8)[...])
        let size = terminal.terminalDimensions
        try await until("PTY resize") { screen().contains("\(size.rows) \(size.cols)") }
        for name in app.palettes.keys {
          app.prefs.palette = name
          app.applyTheme()
        }
        app.prefs.palette = "nord"
        app.applyTheme()
        try require(app.palettes.count == 245, "244 palettes plus classic")
        app.search.stringValue = "nothingmatches"
        app.render()
        try require(app.spaceRows.isEmpty, "search filters")
        app.search.stringValue = ""
        app.render()
        try require(
          app.terminals[key] === terminal && terminal.connected, "search retains terminal")
        // Herdr 0.9.2+ clears reported agents after a pane returns to an idle
        // shell. Keep a disposable foreground process alive while simulating one.
        terminal.send(source: terminal, data: Array("sleep 60\r".utf8)[...])
        var foregroundReady = false
        for _ in 0..<50 {
          let info = try await rpc(session, "pane.process_info", ["pane_id": pane.pane_id])
          if let processInfo = info["process_info"] as? [String: Any],
            let processes = processInfo["foreground_processes"] as? [[String: Any]],
            processes.contains(where: { $0["name"] as? String == "sleep" })
          {
            foregroundReady = true
            break
          }
          try await Task.sleep(nanoseconds: 100_000_000)
        }
        try require(foregroundReady, "disposable agent process started")
        app.hideHud()
        try require(terminal.connected, "hide keeps attachment")
        _ = try await rpc(
          session, "pane.report_agent",
          [
            "pane_id": pane.pane_id, "source": "custom:hud-test", "agent": "hud-test",
            "state": "working",
          ])
        try await until("agent shortcut") { !app.agentRows.isEmpty }
        _ = try await rpc(
          session, "pane.report_agent",
          [
            "pane_id": pane.pane_id, "source": "custom:hud-test", "agent": "hud-test",
            "state": "blocked",
          ])
        try await until("unread event") { app.unread.contains(key) }
        app.show()
        try await until("acknowledgment") { !app.unread.contains(key) }
        try require(app.terminals[key] === terminal, "agent status retains terminal")
        terminal.send(source: terminal, data: [3][...])
        let created = try await rpc(
          session, "workspace.create",
          ["label": "Mac smoke space", "cwd": NSHomeDirectory(), "focus": false])
        guard let root = created["root_pane"] as? [String: Any],
          let secondID = root["terminal_id"] as? String,
          let workspace = root["workspace_id"] as? String
        else { throw HudError.message("Missing created IDs") }
        let secondKey = TerminalKey(session.socket_path, secondID)
        try await until("new space") { app.pane(secondKey) != nil }
        app.select(secondKey)
        try await until("second attachment") { app.terminals[secondKey]?.connected == true }
        let second = app.pane(secondKey)!.2
        _ = try await rpc(
          session, "pane.rename", ["pane_id": second.pane_id, "label": "Renamed terminal"])
        _ = try await rpc(
          session, "tab.rename", ["tab_id": second.tab_id, "label": "Renamed terminal"])
        _ = try await rpc(
          session, "workspace.rename", ["workspace_id": workspace, "label": "Renamed space"])
        try await until("renames") {
          app.spaceRows.contains { $0.title == "Renamed terminal" }
            && app.spaceRows.contains { $0.title == "Renamed space" }
        }
        _ = try await rpc(session, "pane.close", ["pane_id": second.pane_id])
        try await until("close secondary space") {
          app.snapshots[session.socket_path]?.1.workspaces.contains { $0.workspace_id == workspace }
            == false
        }
        app.select(key)
        try require(app.terminals[key] === terminal, "first terminal retained after close")
        terminal.detach()
        try await Task.sleep(nanoseconds: 400_000_000)
        let afterDetach = try await snap(session)
        try require(
          afterDetach.panes.contains { $0.terminal_id == key.id },
          "detach preserves server-owned terminal")
        app.select(key)
        try await until("reattachment") { terminal.connected }
        terminal.send(
          source: terminal, data: Array("printf '\\110\\125\\104_REATTACHED\\n'\r".utf8)[...])
        try await until("input after reattach") { screen().contains("HUD_REATTACHED") }
        app.toggleSidebar()
        app.window.contentView?.layoutSubtreeIfNeeded()
        app.toggleSidebar()
        app.window.contentView?.layoutSubtreeIfNeeded()
        try require(
          app.sidebar.frame.width >= 180 && app.rightPane.frame.minX >= app.sidebar.frame.maxX,
          "sidebar and terminal must not overlap after collapse/restore")
        app.settings()
        app.chooseTheme()
        app.settingsController?.window?.orderOut(nil)
        app.leaveSetup()
        app.setDesktopActive(false)
        try require(!app.bubble.isVisible, "inactive session hides H")
        app.setDesktopActive(true)
        app.save()
        let saved = Preferences.load()
        try require(saved.palette == "nord" && saved.windowFrame.count == 4, "saved preferences")
        let recovered = clampedFrame(
          NSRect(x: 100000, y: 100000, width: 500, height: 300), fallback: app.window.frame)
        try require(NSScreen.screens.contains { recovered.intersects($0.visibleFrame) },
          "offscreen geometry recovery on a connected screen")
        app.window.contentView?.layoutSubtreeIfNeeded()
        if let view = app.window.contentView,
          let rep = view.bitmapImageRepForCachingDisplay(in: view.bounds)
        {
          view.cacheDisplay(in: view.bounds, to: rep)
          if let data = rep.representation(using: .png, properties: [:]) {
            try data.write(to: URL(fileURLWithPath: "/private/tmp/herdr-hud-smoke.png"))
          }
        }
        let herdrVersion = try app.backend.check()
        result =
          "PASS: selection/CLI gesture routes, clipboard text/image fallback, implicit/OSC8 links, retained/live history in both directions, header focus; real \(herdrVersion) create/attach/input, clipboard, resize, 245 palettes, search preservation, agent events/unread, rename/close, detach/reattach, desktop controls, preferences, geometry."
        successful = true
      } catch {
        result = "FAIL: " + error.localizedDescription
        result +=
          "\nPalettes: \(app.palettes.count); split: \(app.split.frame); sections: \(app.sections.frame); host: \(app.terminalHost.frame)"
        if let key = app.selected, let terminal = app.terminals[key] {
          result +=
            "\n" + terminal.terminalStateSnapshot().visibleRows.map(\.text).joined(separator: "\n")
        }
      }
      let layout = [
        "split": app.split.frame, "sections": app.sections.frame,
        "section0": app.sections.subviews[0].frame, "section1": app.sections.subviews[1].frame,
        "spaces": app.spaces.frame, "spaceToggle": app.spaceToggle.frame,
        "agents": app.agents.frame, "host": app.terminalHost.frame,
      ]
      try? String(describing: layout).write(
        toFile: "/private/tmp/herdr-hud-layout.txt", atomically: true, encoding: .utf8)
      if successful && CommandLine.arguments.contains("--smoke-hold") {
        try? await Task.sleep(nanoseconds: 120_000_000_000)
      }
      app.monitor?.stop()
      app.terminals.values.forEach { $0.detach() }
      let backend = app.backend
      if backend.defaultSession.hasPrefix("hud-mac-test-") {
        _ = try? await withCheckedThrowingContinuation {
          (continuation: CheckedContinuation<Data, Error>) in
          app.worker.async {
            do {
              continuation.resume(
                returning: try Host.run(
                  backend.executable(), ["--session", backend.defaultSession, "server", "stop"]))
            } catch { continuation.resume(throwing: error) }
          }
        }
      }
      NSPasteboard.general.clearContents()
      let restored = savedClipboard.map { values in
        let item = NSPasteboardItem()
        for (type, data) in values { item.setData(data, forType: type) }
        return item
      }
      NSPasteboard.general.writeObjects(restored)
      try? result.write(
        toFile: "/private/tmp/herdr-hud-smoke-result.txt", atomically: true, encoding: .utf8)
      print(result)
      if successful { NSApp.terminate(nil) } else { exit(1) }
    }
  }
#endif
