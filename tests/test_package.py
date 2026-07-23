def test_imports_without_gui_side_effects():
    import morse_app.callsigns
    import morse_app.content
    import morse_app.core
    import morse_app.exporters
    import morse_app.gui
    import morse_app.settings

    assert morse_app.core.MORSE_CODES["S"] == "..."
