#if DEBUG
import AppKit
import HudCore

extension SmokeRun {
  func remoteParityChecks() async throws {
    guard let target = ProcessInfo.processInfo.environment["HUD_TEST_REMOTE_TARGET"],
      let name = ProcessInfo.processInfo.environment["HUD_TEST_REMOTE_SESSION"] else { return }
    let data = try JSONSerialization.data(withJSONObject: ["id":"smoke", "label":"Remote smoke", "target":target, "session":name, "enabled":true])
    let profile = try JSONDecoder().decode(MachineProfile.self, from:data)
    let machine = try RemoteMachine(profile:profile, backend:app.backend)
    defer { machine.stop() }
    var received: (Session, Snapshot)?
    var failure: String?
    machine.onSnapshot = { session, snapshot in DispatchQueue.main.async { received = (session, snapshot) } }
    machine.onError = { _, error in DispatchQueue.main.async { failure = error } }
    machine.start()
    try await until("remote snapshot", timeout:20) { received != nil || failure != nil }
    if let failure { throw HudError.message(failure) }
    guard let (session, _) = received else { throw HudError.message("No remote result") }
    let created = try await rpc(session, "workspace.create", ["label":"Mac remote smoke", "focus":false])
    guard let pane = created["root_pane"] as? [String:Any], let id = pane["terminal_id"] as? String,
      let workspace = pane["workspace_id"] as? String else { throw HudError.message("Invalid remote workspace") }
    do {
      let snapshot = try await snap(session)
      app.received(session, snapshot)
      let key = TerminalKey(session.socket_path, id)
      app.select(key)
      guard let terminal = app.terminals[key] else { throw HudError.message("No remote terminal") }
      try await until("remote attach", timeout:10) { terminal.connected }
      try await Task.sleep(nanoseconds:1_000_000_000)
      terminal.send(source:terminal, data:Array("printf 'HUD_SWIFT_REMOTE_%s\\n' SUCCESS\r".utf8)[...])
      try await until("remote keyboard input", timeout:15) {
        terminal.terminalStateSnapshot().visibleRows.map(\.text).joined(separator:"\n").contains("HUD_SWIFT_REMOTE_SUCCESS")
      }
      terminal.detach()
      let after = try await snap(session)
      try require(after.panes.contains { $0.terminal_id == id }, "remote detach preserves pane")
      let identity = machine.session.socket_path
      machine.rename("Renamed remote")
      try require(machine.session.socket_path == identity, "remote rename preserves identity")
      _ = try await rpc(session, "workspace.close", ["workspace_id":workspace])
      app.snapshots.removeValue(forKey:session.socket_path); app.prune(); app.render()
    } catch {
      _ = try? await rpc(session, "workspace.close", ["workspace_id":workspace])
      throw error
    }
  }

  func parityChecks(_ session: Session) async throws {
    try await remoteParityChecks()
    let snapshot = try await snap(session)
    guard let pane = snapshot.panes.first else { throw HudError.message("Missing parity-test pane") }
    let key = TerminalKey(session.socket_path, pane.terminal_id)
    let cached = app.terminalIdentities[key]
    app.terminalIdentities[key] = "tester@remote"
    try require(app.userHost(session, pane) == (titleIdentity(pane.terminal_title_stripped) ?? "tester@remote"),
      "identity tooltip uses reported or remembered identity")
    app.terminalIdentities[key] = cached
    if ProcessInfo.processInfo.environment["HUD_TEST_REAL_CODEX"] == "1" {
      let created = try await rpc(session, "workspace.create", ["label": "Codex parity", "focus": false])
      guard let first = created["root_pane"] as? [String: Any],
        let workspace = first["workspace_id"] as? String,
        let firstID = first["pane_id"] as? String else { throw HudError.message("Invalid workspace reply") }
      let added = try await rpc(session, "tab.create", ["workspace_id": workspace, "focus": false])
      guard let second = added["root_pane"] as? [String: Any], let secondID = second["pane_id"] as? String else {
        throw HudError.message("Invalid tab reply")
      }
      for (index, id) in [firstID, secondID].enumerated() {
        let backend = app.backend
        try await withCheckedThrowingContinuation { (continuation: CheckedContinuation<Void, Error>) in
          app.worker.async {
            do {
              _ = try Host.run(backend.executable(), ["--session", session.name, "agent", "start",
                "parity-\(index)", "--kind", "codex", "--pane", id, "--timeout", "30000"], timeout: 40)
              continuation.resume()
            } catch { continuation.resume(throwing: error) }
          }
        }
      }
      let final = try await snap(session)
      let agents = final.panes.filter { $0.workspace_id == workspace && $0.agent == "codex" }
      try require(agents.count == 2, "two independently started real Codex agents are detected")
      app.received(session, final)
      try require(app.agentRows.filter { $0.workspace == workspace }.count == 2, "two real Codex shortcuts")
      try require(Set(agents.map(\.terminal_id)).count == 2, "distinct real Codex terminal identities")
    }
  }
}
#endif
