import { describe, it, expect } from "vitest"
import { cn } from "./utils"

describe("cn", () => {
  it("joins plain class strings", () => {
    expect(cn("a", "b")).toBe("a b")
  })

  it("drops falsy values", () => {
    expect(cn("a", false && "b", null, undefined, "c")).toBe("a c")
  })

  it("merges conflicting tailwind classes, keeping the last one", () => {
    // tailwind-merge should resolve conflicting utilities to the last value
    expect(cn("px-2", "px-4")).toBe("px-4")
  })

  it("supports conditional object-less usage via arrays", () => {
    expect(cn(["a", "b"], "c")).toBe("a b c")
  })
})
