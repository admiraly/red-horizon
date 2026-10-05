# Licensed source models and animation

The starter model pack is baked offline from nine selected author model roles. It contains high and low detail geometry for infantry, armor, artillery, distinct bomber and fighter roles, the first-person rifle, fortifications, trees and buildings. Original source files stay outside the repository and release. `content/model-sources.json` pins their download URLs, original SHA256 values and archive members; `content/asset-manifest.json` connects each source to the distributed derivative and credit.

Quaternius's selected Toon Shooter Game Kit and Animated Tanks pack pages explicitly link CC0. The downloaded tanks license also specifies CC0. His current global license page separately describes QAL v1.0; these records concern the specific older packs, rather than a blanket claim about all current Quaternius assets. Pack-specific evidence is recorded under `content/licenses/`. Captain_Ahab_62's [fighter jets submission](https://opengameart.org/content/fighter-jets) explicitly grants CC0 and requests voluntary credit. Its pinned archive contains the source-named F-111 Aardvark fuselage plus left/right wings and Eurofighter. The F-111 is a [tactical fighter-bomber](https://www.nationalmuseum.af.mil/Visit/Museum-Exhibits/Fact-Sheets/Display/Article/196049/general-dynamics-f-111a-aardvark/), used for bomber mesh role 3; Eurofighter uses fighter mesh role 8. These replace the spacecraft surrogate with distinct military winged geometry. The bomber is not a heavy strategic bomber. Source files are identical copies of the shared archive member renamed F111.blend and Eurofighter.blend for role-specific selection. License evidence is in `content/licenses/Captain-Ahab-Fighter-Jets.txt`. The artillery role uses the second selected authored tank model.

Soldier animation comes from authored Idle, Walk, Run_Gun and Idle_Shoot actions. The two tanks have authored forward-motion actions. The rifle, aircraft and environmental props are static source meshes; their world motion and first-person presentation come from the existing game. No skeletal animation is claimed for those files. `content/models/bake-report.json` records source hashes, Blender version, selected actions, frame counts, distinct frame hashes, geometry budgets and bounds.

Rebuilding the installed pack is optional development work:

```sh
python3 tools/fetch_models.py
blender -b --python tools/bake_models.py -- \
  --sources .tools/asset-sources \
  --output content/models/battle.rham \
  --report content/models/bake-report.json
python3 tools/models.py content/models/battle.rham
```

Blender and Python do not run in the game. The converter triangulates and simplifies source geometry before skinning, then samples the authored actions at 12 fps with fixed vertex correspondence. The renderer interpolates baked frames on the GPU. Source material colors are retained as vertex RGB. Assets are normalized to metres with forward +Z and feet/base Y=0. Derived hashes and the network content fingerprint must be refreshed after a rebake.

RHAM version 1 has a 48-byte header, 64-byte mesh descriptors and 16-byte clip descriptors. Frame geometry consists of three vec4 values per expanded triangle vertex: position, normal and source color. Mesh descriptors include role, detail level, vertex/frame ranges, clip ranges, scale, radius and XYZ dimensions. Clip semantics are idle=0, walk=1, run=2 and fire=3. The installed pack is bounded to 64 MiB, 32 mesh records, 128 clip records and 128 frames per mesh. The assembly loader validates the binary before uploading it; the offline validator additionally requires every rendered category/detail pair and genuinely changing infantry locomotion frames.

Animation is cosmetic. It follows observed positions, generations and firing records without writing authoritative game state. Nearby source models use a bounded detail budget, medium-distance actors use simplified source geometry and distant actors retain visible role/team markers. Static fortifications are fitted to existing solid dimensions. Decorative trees add no new cover semantics. This is a starter art integration, not production rigging, weapon attachment IK, military vehicle variants, destructible buildings or reference-hardware GPU acceptance.

The aircraft replacement used `--config` with roles 3/8 and `--replace-pack`/`--replace-report` on the previously verified pack. This retains all unselected role geometry and clips byte-for-byte. Full rebakes use the same selections in DEFAULTS. Aircraft high LOD budgets are 1,500 triangles, low LOD 96; installed counts are F-111 1,378/86 and Eurofighter 1,332/87. Lengths are 22 m and 16 m with uniform instance scale. Wings and gear are static authored configurations. Runtime AIR_ROLE selects role 8 only for a matching active sidecar; stale/recycled actors use role 3 fallback. RHAM v1 and entity kind 3 remain unchanged; the required category set now includes role 8 in both LODs.

For a bounded aircraft-only update, retain the existing pack/report under temporary paths, then run:

```sh
blender -b --python tools/bake_models.py -- \
  --sources .tools/asset-sources --roles 3 8 \
  --replace-pack /path/to/prior.rham --replace-report /path/to/prior-report.json \
  --output content/models/battle.rham --report content/models/bake-report.json
```

Update all RHAM manifest derivative hashes and regenerate credits with `python3 tools/assets.py`; refresh the network fingerprint before integration.

Replacement verification on Mesa 26.2.3 software OpenGL 4.6: real client aircraft pose/altitude/role and authority encounters pass; normalized fighter/bomber top-view mask overlap is 0.6224, excluding size and palette as the sole distinction. Infantry idle comparison changes 536 pixels with distinct source frames; tactical movement selects the authored walk, and stationary tank tracks remain frozen. All fourteen unaffected role/LOD records retain identical geometry, clips and descriptor metadata (apart from table offsets). Asset/hash validation and the fast suite pass; the assembly loader rejects a missing fighter category in addition to malformed/nonfinite cases. These checks establish sourced geometry and the exercised rendering paths, not visual production quality or target-GPU massive-battle performance.
