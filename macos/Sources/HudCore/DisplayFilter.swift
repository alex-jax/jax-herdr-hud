import Foundation

/// Keep CLI foreground/background pairs and controls intact. Only palette assignments
/// are suppressed, so applications cannot replace the user's Hud palette.
public final class DisplayFilter {
  private var pending: [UInt8] = []
  private var state = 0 // text, escape, CSI, OSC, control string, string escape
  public init() {}
  public func reset() { pending = []; state = 0 }
  public func feed(_ bytes: ArraySlice<UInt8>) -> [UInt8] {
    var output: [UInt8] = []
    for byte in bytes {
      switch state {
      case 0:
        if byte == 27 { pending = [byte]; state = 1 } else { output.append(byte) }
      case 1:
        pending.append(byte)
        if byte == 91 { state = 2 }
        else if byte == 93 { state = 3 }
        else if [80, 88, 94, 95].contains(byte) {
          output += pending; pending = []; state = 4
        } else { output += pending; pending = []; state = 0 }
      case 4, 5:
        output.append(byte)
        state = state == 5 && byte == 92 ? 0 : byte == 27 ? 5 : 4
      default:
        pending.append(byte)
        let complete = state == 2 ? (0x40...0x7e).contains(byte)
          : byte == 7 || pending.suffix(2).elementsEqual([27, 92])
        if complete {
          let selector = String(decoding: pending.dropFirst(2).prefix { $0 != 59 && $0 != 7 && $0 != 27 }, as: UTF8.self)
          let palette = ["4", "10", "11", "12", "104", "110", "111", "112"].contains(selector)
          if state != 3 || !palette || pending.contains(63) { output += pending }
          pending = []; state = 0
        } else if pending.count > 65536 { output += pending; pending = []; state = 0 }
      }
    }
    return output
  }
}
