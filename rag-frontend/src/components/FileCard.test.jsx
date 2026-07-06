import { describe, it, expect, vi } from "vitest"
import { render, screen, fireEvent } from "@testing-library/react"
import { FileCard, FileChip, fileMeta, formatFileSize } from "./FileCard"

describe("formatFileSize", () => {
  it("returns an empty string for 0 or missing bytes", () => {
    expect(formatFileSize(0)).toBe("")
    expect(formatFileSize(undefined)).toBe("")
  })

  it("formats bytes under 1KB", () => {
    expect(formatFileSize(512)).toBe("512 B")
  })

  it("formats kilobytes", () => {
    expect(formatFileSize(2048)).toBe("2.0 KB")
  })

  it("formats megabytes", () => {
    expect(formatFileSize(5 * 1024 * 1024)).toBe("5.0 MB")
  })
})

describe("fileMeta", () => {
  it("recognizes known extensions", () => {
    expect(fileMeta("invoice.pdf").color).toBe("#F87171")
    expect(fileMeta("sheet.xlsx").color).toBe("#34D399")
  })

  it("falls back to a default for unknown extensions", () => {
    expect(fileMeta("weird.xyz").color).toBe("#A1A1AA")
  })

  it("is case-insensitive", () => {
    expect(fileMeta("REPORT.PDF").color).toBe(fileMeta("report.pdf").color)
  })
})

describe("FileCard", () => {
  it("renders the file name and ready status", () => {
    render(<FileCard file={{ name: "report.pdf", status: "ready", size: 1024 }} />)
    expect(screen.getByText("report.pdf")).toBeInTheDocument()
    expect(screen.getByText("Ready")).toBeInTheDocument()
  })

  it("calls onPreview when a ready card is clicked", () => {
    const onPreview = vi.fn()
    render(<FileCard file={{ name: "report.pdf", status: "ready" }} onPreview={onPreview} />)
    fireEvent.click(screen.getByRole("button", { name: /report\.pdf/i }))
    expect(onPreview).toHaveBeenCalledWith("report.pdf")
  })

  it("shows a cancel-indexing action while indexing and does not trigger preview", () => {
    const onCancelIndexing = vi.fn()
    const onPreview = vi.fn()
    render(
      <FileCard
        file={{ name: "slides.pptx", status: "indexing", progress: { current: 2, total: 4 } }}
        onCancelIndexing={onCancelIndexing}
        onPreview={onPreview}
      />
    )
    fireEvent.click(screen.getByText("Cancel indexing"))
    expect(onCancelIndexing).toHaveBeenCalledWith("slides.pptx")
    expect(onPreview).not.toHaveBeenCalled()
  })
})

describe("FileChip", () => {
  it("renders the file name", () => {
    render(<FileChip file={{ name: "notes.txt", status: "ready" }} />)
    expect(screen.getByText("notes.txt")).toBeInTheDocument()
  })

  it("calls onRemove without triggering onPreview", () => {
    const onRemove = vi.fn()
    const onPreview = vi.fn()
    render(<FileChip file={{ name: "notes.txt", status: "ready" }} onRemove={onRemove} onPreview={onPreview} />)
    fireEvent.click(screen.getByRole("button", { name: /remove notes\.txt/i }))
    expect(onRemove).toHaveBeenCalledWith("notes.txt")
    expect(onPreview).not.toHaveBeenCalled()
  })
})
