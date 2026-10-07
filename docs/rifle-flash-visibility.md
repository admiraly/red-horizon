# Rifle flash observer visibility

The actual finite NPC rifle test now declares a camera20m sideways from the
source/target firing line. Its old collinear view placed the target20m in front
of the source flash; authored body animation can completely occlude the0.25m
flash. This is a fixed initial viewing fixture, retaining both actors, their
finite original stocks, actual AI firing, and strict paired cosmetic/authority
checks. No runtime graphics or simulation behavior changes.

The exact immutable full-checkpoint7dc8436c715c binary that failed the old gate
passes with11paired changed pixels; the new aircraft cannon candidate passes
with9. That older full checkpoint remains failed. This focused observer
correction does not prove general flash visibility or spectacle. Exact binary
hashes/results: evidence/rifle-flash-clear-view.json.
