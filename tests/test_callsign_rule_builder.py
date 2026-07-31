import json

from tools.build_callsign_rules import build


def test_builder_handles_spratly_entity_without_simple_prefix(tmp_path):
    source = {
        "dxcc": [
            {
                "deleted": False,
                "entityCode": 247,
                "countryCode": "ZZ",
                "name": "Spratly Islands",
                "prefix": "",
                "prefixRegex": "^1S[A-Z0-9/]*$",
            }
        ]
    }
    territories = {
        "main": {
            "zh-Hans": {
                "localeDisplayNames": {"territories": {"ZZ": "未知地区"}}
            }
        }
    }
    source_path = tmp_path / "source.json"
    territories_path = tmp_path / "territories.json"
    output_path = tmp_path / "output.json"
    source_path.write_text(json.dumps(source), encoding="utf-8")
    territories_path.write_text(json.dumps(territories), encoding="utf-8")

    build(source_path, territories_path, output_path, expected_count=1)

    entity = json.loads(output_path.read_text(encoding="utf-8"))["entities"][0]
    assert entity["name_zh"] == "南沙群岛"
    assert entity["prefixes"] == ["1S"]


def test_builder_disambiguates_entities_with_same_country_and_prefix(tmp_path):
    items = []
    for entity_id, name in ((9, "American Samoa"), (515, "Swains Island")):
        items.append(
            {
                "deleted": False,
                "entityCode": entity_id,
                "countryCode": "AS",
                "name": name,
                "prefix": "KH8",
                "prefixRegex": "^KH8[A-Z0-9/]*$",
            }
        )
    source_path = tmp_path / "source.json"
    territories_path = tmp_path / "territories.json"
    output_path = tmp_path / "output.json"
    source_path.write_text(json.dumps({"dxcc": items}), encoding="utf-8")
    territories_path.write_text(
        json.dumps(
            {
                "main": {
                    "zh-Hans": {
                        "localeDisplayNames": {"territories": {"AS": "美属萨摩亚"}}
                    }
                }
            }
        ),
        encoding="utf-8",
    )

    build(source_path, territories_path, output_path, expected_count=2)

    names = [
        item["name_zh"]
        for item in json.loads(output_path.read_text(encoding="utf-8"))["entities"]
    ]
    assert set(names) == {"美属萨摩亚（KH8，实体9）", "美属萨摩亚（KH8，实体515）"}
