import { describe, it, expect, vi } from "vitest"
import { render, screen, fireEvent } from "@testing-library/react"
import { Composer } from "./Composer"
import { TooltipProvider } from "@/components/ui/tooltip"

function setup(overrides = {}) {
  const props = {
    value: "",
    onChange: vi.fn(),
    onSubmit: vi.fn(e => e.preventDefault()),
    isLoading: false,
    onCancel: vi.fn(),
    streamMode: true,
    onToggleStream: vi.fn(),
    onAttach: vi.fn(),
    showUrl: false,
    onToggleUrl: vi.fn(),
    urlValue: "",
    onUrlChange: vi.fn(),
    onUrlSubmit: vi.fn(e => e.preventDefault()),
    urlLoading: false,
    provider: "local",
    onProviderChange: vi.fn(),
    cloudModel: "",
    onCloudModelChange: vi.fn(),
    cloudModels: [],
    files: [],
    onPreviewFile: vi.fn(),
    onRemoveFile: vi.fn(),
    ...overrides,
  }
  render(
    <TooltipProvider>
      <Composer {...props} />
    </TooltipProvider>
  )
  return props
}

describe("Composer", () => {
  it("renders the message textarea", () => {
    setup()
    expect(screen.getByLabelText("Message")).toBeInTheDocument()
  })

  it("calls onChange when typing", () => {
    const props = setup()
    fireEvent.change(screen.getByLabelText("Message"), { target: { value: "hello" } })
    expect(props.onChange).toHaveBeenCalledWith("hello")
  })

  it("disables the send button when the input is empty", () => {
    setup({ value: "" })
    expect(screen.getByLabelText("Send message")).toBeDisabled()
  })

  it("enables the send button once there is text", () => {
    setup({ value: "hello" })
    expect(screen.getByLabelText("Send message")).not.toBeDisabled()
  })

  it("submits on Enter without shift", () => {
    const props = setup({ value: "hello" })
    fireEvent.keyDown(screen.getByLabelText("Message"), { key: "Enter", shiftKey: false })
    expect(props.onSubmit).toHaveBeenCalled()
  })

  it("does not submit on Shift+Enter", () => {
    const props = setup({ value: "hello" })
    fireEvent.keyDown(screen.getByLabelText("Message"), { key: "Enter", shiftKey: true })
    expect(props.onSubmit).not.toHaveBeenCalled()
  })

  it("shows a stop button instead of send while loading", () => {
    setup({ isLoading: true })
    expect(screen.getByLabelText("Stop generating")).toBeInTheDocument()
    expect(screen.queryByLabelText("Send message")).not.toBeInTheDocument()
  })

  it("calls onCancel when the stop button is clicked", () => {
    const props = setup({ isLoading: true })
    fireEvent.click(screen.getByLabelText("Stop generating"))
    expect(props.onCancel).toHaveBeenCalled()
  })

  it("switches provider when clicking the Groq option", () => {
    const props = setup({ provider: "local" })
    fireEvent.click(screen.getByRole("radio", { name: "Groq" }))
    expect(props.onProviderChange).toHaveBeenCalledWith("cloud")
  })

  it("calls onAttach when the attach button is clicked", () => {
    const props = setup()
    fireEvent.click(screen.getByLabelText("Attach files"))
    expect(props.onAttach).toHaveBeenCalled()
  })
})
