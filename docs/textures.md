# Terrain texture sources and offline bake

The temperate battlefield uses real photographed Leafy Grass, Brown Mud, Gravel Ground 01 and Rocky Terrain diffuse maps from Poly Haven. Original authors are Charlotte Baglioni, Rob Tuytel and Amal Kumar. The author's asset licence is CC0; original source URLs, API metadata hashes, exact download hashes and licence evidence are pinned in `content/texture-sources.json`. Downloaded website pages and preview images are not distributed as game assets. Voluntary credits appear in `content/CREDITS.md` and `THIRD_PARTY.md`.

The shipped `content/textures/terrain.rhtx` contains four opaque, bottom-up 512×512 RGBA8 layers. `tools/bake_textures.py` verifies the original 1024×1024 JPEG hashes, resizes with Pillow Lanczos, flips vertically and writes a bounded raw pack. It neither recolours the photographs nor substitutes generated textures. Original sources remain under ignored `.tools/texture-sources/`; only the baked derivative is distributed. The pack is 4,194,336 bytes, SHA256 `9abd8af59d55a19fb123f5d5a64dd9a16f27e653c908ac342c192d1cfaf836bc`. Two local bakes produced identical bytes and layer hashes.

To reproduce the bake, install Pillow as an offline development dependency and run:

```sh
python3 tools/bake_textures.py --fetch
python3 tools/assets.py
```

The optional fetch downloads only missing pinned original diffuse files. The normal game and asset validator use neither Pillow nor a runtime image decoder. The validator checks original provenance against manifest entries, exact pack/header/layer hashes, opaque alpha and actual colour variation. See [rendering and weather](environment-renderer.md) for runtime behavior and actual graphics evidence. These are diffuse-only materials; authored normal/roughness maps, vegetation ground cover, puddles, snow, rain audio and weather affecting gameplay remain future work.
