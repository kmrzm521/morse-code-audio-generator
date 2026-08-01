def test_imports_without_gui_side_effects():
    import morse_app.callsigns
    import morse_app.content
    import morse_app.core
    import morse_app.exporters
    import morse_app.gui
    import morse_app.settings

    assert morse_app.core.MORSE_CODES["S"] == "..."


def test_main_package_includes_offline_rules_and_public_key_only():
    spec = open("morse-generator.spec", encoding="utf-8").read()
    assert "global_callsign_rules.json" in spec
    assert "public_key.txt" in spec
    assert "owner-private-key.txt" not in spec
    assert "license_admin" not in spec


def test_owner_package_does_not_embed_private_key():
    spec = open("license-admin.spec", encoding="utf-8").read()
    assert "owner-private-key.txt" not in spec
