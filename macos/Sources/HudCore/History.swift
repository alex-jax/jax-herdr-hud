import Foundation

/// Scroll matching shared by the live CLI selection and its regression checks.
public struct ScrollOverlap {
  public let head: Int
  public let old: [String]
  public let new: [String]
  public let shift: Int

  public static func match(_ previous: [String], _ current: [String], direction: Int) -> ScrollOverlap? {
    let size = min(previous.count, current.count)
    guard size >= 3 else { return nil }
    var head = 0, tail = 0
    while head < size && previous[head] == current[head] { head += 1 }
    while tail < size - head && previous[previous.count - tail - 1] == current[current.count - tail - 1] { tail += 1 }
    let old = Array(previous[head..<(previous.count - tail)])
    let new = Array(current[head..<(current.count - tail)])
    let count = min(old.count, new.count)
    if count > 2 {
      for overlap in stride(from: count - 1, through: 2, by: -1) {
        let left = direction > 0 ? Array(old.suffix(overlap)) : Array(old.prefix(overlap))
        let right = direction > 0 ? Array(new.prefix(overlap)) : Array(new.suffix(overlap))
        if left == right && left.filter({ !$0.trimmingCharacters(in: .whitespaces).isEmpty }).count >= 2 {
          return ScrollOverlap(head: head, old: old, new: new,
            shift: direction > 0 ? old.count - overlap : -(new.count - overlap))
        }
      }
    }
    // A changed footer is allowed only alongside a substantial contiguous match.
    var best: (length: Int, head: Int, end: Int, shift: Int)?
    if size > 3 {
      for distance in 1..<(size - 2) {
        let delta = direction > 0 ? distance : -distance
        var run = 0
        for oldRow in max(0, delta)..<min(previous.count, current.count + delta) {
          let newRow = oldRow - delta
          run = previous[oldRow] == current[newRow] ? run + 1 : 0
          guard run >= max(3, size / 2),
            previous[(oldRow-run+1)...oldRow].filter({ !$0.trimmingCharacters(in: .whitespaces).isEmpty }).count >= 3 else { continue }
          if best == nil || run > best!.length {
            best = (run, min(oldRow, newRow) - run + 1, max(oldRow, newRow) + 1, delta)
          }
        }
      }
    }
    guard let best else { return nil }
    return ScrollOverlap(head: best.head, old: Array(previous[best.head..<best.end]),
      new: Array(current[best.head..<best.end]), shift: best.shift)
  }
}
