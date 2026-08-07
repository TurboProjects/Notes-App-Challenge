class ResizeObserverStub {
  observe() {}
  unobserve() {}
  disconnect() {}
}

window.ResizeObserver = window.ResizeObserver || ResizeObserverStub
window.Element.prototype.scrollIntoView = window.Element.prototype.scrollIntoView || (() => {})
window.Element.prototype.hasPointerCapture = window.Element.prototype.hasPointerCapture || (() => false)
window.Element.prototype.setPointerCapture = window.Element.prototype.setPointerCapture || (() => {})
window.Element.prototype.releasePointerCapture = window.Element.prototype.releasePointerCapture || (() => {})
