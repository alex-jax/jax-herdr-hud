import AppKit
import HudCore

extension HudApp {
  func startUpdates() {
    guard !CommandLine.arguments.contains("--smoke-test") else { return }
    let current = Bundle.main.object(forInfoDictionaryKey: "CFBundleShortVersionString") as? String ?? "1.5"
    if let data = UserDefaults.standard.data(forKey: "HudAvailableUpdate"),
      let release = try? JSONDecoder().decode(HudRelease.self, from: data),
      HudUpdates.newer(release.tag_name, than: current) {
      availableUpdate = release; updateButton.isHidden = false
    }
    updateTimer = Timer.scheduledTimer(withTimeInterval: 60, repeats: true) { [weak self] _ in
      self?.checkUpdates(manual: false)
    }
    checkUpdates(manual: false)
  }
  @objc func checkForUpdates() { checkUpdates(manual: true) }
  func checkUpdates(manual: Bool) {
    guard !updateBusy, !closing else { return }
    let last = UserDefaults.standard.double(forKey: "HudUpdateChecked")
    if !manual && Date().timeIntervalSince1970 - last < HudUpdates.interval { return }
    updateBusy = true
    UserDefaults.standard.set(Date().timeIntervalSince1970, forKey: "HudUpdateChecked")
    let current = Bundle.main.object(forInfoDictionaryKey: "CFBundleShortVersionString") as? String ?? "1.5"
    if manual { status.stringValue = "Checking for updates…" }
    DispatchQueue.global().async { [weak self] in
      let result = Result { try HudUpdates.choose(HudUpdates.releases(), current: current) }
      DispatchQueue.main.async {
        guard let self, !self.closing else { return }
        self.updateBusy = false
        switch result {
        case .success(let release):
          self.availableUpdate = release
          if let release, let data = try? JSONEncoder().encode(release) {
            UserDefaults.standard.set(data, forKey: "HudAvailableUpdate")
          } else { UserDefaults.standard.removeObject(forKey: "HudAvailableUpdate") }
          self.updateButton.isHidden = release == nil
          if let release {
            self.updateButton.toolTip = "Download Herdr Hud " + release.tag_name
            if manual { self.status.stringValue = "Update available: " + release.tag_name + ". Click the download arrow." }
          } else if manual { self.status.stringValue = "Herdr Hud " + current + " is up to date." }
        case .failure(let error):
          if manual { self.status.stringValue = "Update check failed: " + error.localizedDescription }
        }
      }
    }
  }
  @objc func downloadUpdate() {
    guard let release = availableUpdate, !updateBusy else { return }
    updateBusy = true; updateButton.isEnabled = false
    status.stringValue = "Downloading and verifying " + release.tag_name + "…"
    DispatchQueue.global().async { [weak self] in
      let result = Result { try HudUpdates.installer(release) }
      DispatchQueue.main.async {
        guard let self, !self.closing else { return }
        self.updateBusy = false; self.updateButton.isEnabled = true
        switch result {
        case .success(let url):
          NSWorkspace.shared.open(url)
          self.status.stringValue = "Installer opened. Quit Hud, replace the app, then reopen. Your sessions keep running."
        case .failure(let error): self.status.stringValue = "Update not installed: " + error.localizedDescription
        }
      }
    }
  }
}
