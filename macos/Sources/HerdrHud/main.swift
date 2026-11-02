import AppKit

#if DEBUG
  let isSmokeTest = CommandLine.arguments.contains("--smoke-test")
  if isSmokeTest {
    let root = "/private/tmp/hud-mac-" + UUID().uuidString.prefix(8)
    try FileManager.default.createDirectory(atPath: root, withIntermediateDirectories: true)
    setenv("HUD_TEST_SESSION", "hud-mac-test-" + UUID().uuidString.prefix(8), 1)
    setenv("HUD_TEST_CONFIG", root + "/hud", 1)
    setenv("XDG_CONFIG_HOME", root, 1)
  }
#else
  let isSmokeTest = false
#endif
let application = NSApplication.shared
let identity = "io.github.herdr.Hud"
let existing = NSRunningApplication.runningApplications(withBundleIdentifier: identity).first {
  $0.processIdentifier != ProcessInfo.processInfo.processIdentifier
}
if let existing, !isSmokeTest {
  if CommandLine.arguments.contains("--quit") {
    existing.terminate()
  } else if !CommandLine.arguments.contains("--background") {
    DistributedNotificationCenter.default().postNotificationName(
      NSNotification.Name("io.github.herdr.Hud.show"), object: nil, userInfo: nil,
      deliverImmediately: true)
    existing.activate(options: [.activateAllWindows])
  }
  exit(0)
}
application.setActivationPolicy(.regular)
HudStyle.registerFonts()
let delegate = HudApp()
application.delegate = delegate
application.run()
