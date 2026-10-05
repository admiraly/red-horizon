# Licensed source models and animation

The starter model pack is baked offline from eight downloaded author models. It contains high and low detail geometry for infantry, armor, artillery, the air role, the first-person rifle, fortifications, trees and buildings. Original source files stay outside the repository and release. `content/model-sources.json` pins their download URLs, original SHA256 values and archive members; `content/asset-manifest.json` connects each source to the distributed derivative and credit.

Quaternius's selected Toon Shooter Game Kit and Animated Tanks pack pages explicitly link CC0. The downloaded tanks license also specifies CC0. His current global license page separately describes QAL v1.0; these records concern the specific older packs, rather than a blanket claim about all current Quaternius assets. Pack-specific evidence is recorded under `content/licenses/`. Kenney's Space Kit has both an author-page CC0 grant and a bundled CC0 license. The winged Kenney craft is a stylized spacecraft mapped to the existing air role, not a military jet. The artillery role uses the second selected authored tank model.

Soldier animation comes from authored Idle, Walk, Run_Gun and Idle_Shoot actions. The two tanks have authored forward-motion actions. The rifle, craft and environmental props are static source meshes; their world motion and first-person presentation come from the existing game. No skeletal animation is claimed for those files. `content/models/bake-report.json` records source hashes, Blender version, selected actions, frame counts, distinct frame hashes, geometry budgets and bounds.

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
