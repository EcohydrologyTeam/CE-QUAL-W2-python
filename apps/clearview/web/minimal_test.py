#!/usr/bin/env python3
"""
Absolute minimal Panel test to diagnose the issue
"""

import panel as pn

# Enable Panel
pn.extension()

def create_minimal_app():
    """Create the simplest possible working Panel app"""
    
    # Counter for testing
    counter = pn.pane.Markdown("**Counter: 0**")
    
    def increment(event):
        current = int(counter.object.split(": ")[1].replace("*", ""))
        new_count = current + 1
        counter.object = f"**Counter: {new_count}**"
        print(f"Button clicked! Counter now: {new_count}")
    
    # Simple button
    button = pn.widgets.Button(name="Click Me!", button_type='primary')
    button.on_click(increment)
    
    # Simple layout
    app = pn.Column(
        "# 🧪 Minimal Panel Test",
        "If you can see this text and the button works, Panel is functioning.",
        counter,
        button,
        "---",
        "**Instructions:**",
        "1. Click the button above",
        "2. The counter should increment",
        "3. Check the terminal for debug messages",
        width=400,
        margin=20
    )
    
    return app

if __name__ == "__main__":
    print("🧪 Starting MINIMAL Panel Test...")
    print("🌐 Open browser to: http://localhost:5009")
    print("🔍 Check browser console (F12) for JavaScript errors")
    
    app = create_minimal_app()
    app.show(port=5009, show=True)