// ponytail: Streamlit exposes no autofocus API; update selector if its input markup changes.
(() => {
    let page;
    try {
        page = window.parent.document;
    } catch (_) {
        return; // Cross-origin hosts keep normal click-to-type behavior.
    }
    const host = window.parent;
    if (host.chatComposerKeydown) {
        page.removeEventListener("keydown", host.chatComposerKeydown);
    }
    host.chatComposerKeydown = (event) => {
        if (event.defaultPrevented || event.isComposing || event.ctrlKey || event.metaKey ||
            event.altKey || event.key.length !== 1 || event.key === " ") return;
        const target = event.target;
        if (target.isContentEditable || target.closest(
            'input, textarea, select, button, a, [role="button"], [role="textbox"], [role="dialog"], [tabindex]'
        )) return;
        if (host.getSelection()?.toString()) return;
        const input = page.querySelector('input[placeholder="Tulis pesan..."]');
        if (!input || input.disabled || input.readOnly || !input.getClientRects().length) return;
        event.preventDefault();
        input.focus({preventScroll: true});
        const value = input.value + event.key;
        Object.getOwnPropertyDescriptor(host.HTMLInputElement.prototype, "value").set.call(input, value);
        input.dispatchEvent(new host.Event("input", {bubbles: true}));
        input.setSelectionRange(value.length, value.length);
    };
    page.addEventListener("keydown", host.chatComposerKeydown);
})();
