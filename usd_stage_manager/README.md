# USD Stage Manager 2.0.1 — Blender 5.2

A Solaris-inspired USD stage browser and working-layer editor, rewritten from
SMUELDigital's USD Asset Manager. Tested with Blender 5.2.2 LTS on Linux.
Uses Blender's bundled OpenUSD Python modules; no pip install, Qt or external
USD installation is required on the tested official Blender build.

## Install

1. Disable the old USD Asset Manager / USD Layers Panel add-on. Its automatic
   parenting handler can interfere with your scene while both are enabled.
2. In Blender 5.2, open **Edit → Preferences → Add-ons → menu → Install from Disk**.
3. Select `USD_Stage_Manager_Blender52_v2.0.1.zip` and enable USD Stage Manager.
4. In the 3D View press **N → USD Stage → Open Embedded USD Stage**.
   The same panels are in **Properties → Scene → USD Stage Manager**.

The stage opens as a docked Properties area below the 3D Viewport in the same
Blender window. Repeated clicks reuse the pane. Drag the divider to resize it;
save the .blend with Load UI enabled when reopening to retain the layout.
The pane is pinned to the scene it was opened for and contains native panels. It is not a new compiled editor type, a LOP node network or a
Hydra viewport. The initial pane takes 40% of the viewport height. It creates no floating window.

## Quick start

- **Open** a `.usd`, `.usda`, `.usdc` or `.usdz` file. When replacing an existing
  stage, save it first and enable **Replace current working stage** in the file
  browser. Or choose **New** for an empty `/World` stage.
- Expand the scene graph with triangles. Search by prim path or schema type.
  Search includes matching ancestors and temporarily ignores collapsed branches.
- Select a prim for its attributes, relationships, variants and opinion stack.
  The eye authors visibility; the checkbox authors activation. Payload controls
  load or unload contents. Visibility inherited from a hidden ancestor still
  applies to children; reveal the ancestor first.
- **Reference / Payload** composes an asset under a new absolute prim path.
  The referenced file must have a default prim.
- **USD Layer Stack** adds, removes, mutes and reorders direct source sublayers,
  strongest at the top. All edits go to the separate, strongest working layer.
  Nested sublayers and reference layers can be inspected in Prim Composition;
  this version does not edit those source files directly.
- **Undo USD / Redo USD** reverse stage operations independently of Blender's
  Ctrl-Z. Up to 32 stage edits are retained per open session. USD history is not
  stored in `.blend` files, but the current working stage and load/mute state are.
- **Refresh Viewport** imports the composed stage into a managed preview collection.
  Refresh replaces that collection's objects; it preserves unrelated objects.
  Objects explicitly linked to another collection are retained. Do not make
  final modeling edits on preview objects if you plan to refresh them.
- **Save As** writes the working layer with its source sublayers. **Flatten
  composition** writes one composed layer and bakes the current variant choices.
  Source-layer filenames are protected from overwrite. The save dialog confirms
  overwriting other existing files.

Try `examples/demo.usda` inside the installed add-on directory. Select
`/World/Asset`, choose Cube or Sphere in the `shape` variant menu, then refresh
its viewport preview.

## Blender scene workflow (original add-on functionality)

The **Blender Scene ↔ USD** panel includes:

- **Organize Blender Scene for USD**: explicitly creates tagged World, geo,
  lights, cameras and extras empties. Keeps existing hierarchies and world
  transforms, skips preview objects and linked library objects, and is safe to
  run twice. It does not continuously reparent objects or convert materials to
  fake empty objects. Armature/complex hierarchies remain together under extras.
- **Export Blender Scene to USD**: selected/all objects, animation, materials and
  `/World` root using Blender's native exporter. Uses only properties present in
  the installed Blender RNA API. Blender's native USD export dialog remains
  available from File → Export for advanced settings.
- **Import USD as Editable Blender Objects**: Blender's native USD import dialog.

## Persistence and limits

- `.blend` files store the working USD layer text, layer paths, mute state and
  payload load choices. Referenced assets and textures remain external files.
  Anonymous working opinions are restored lazily after reopening the `.blend`.
- Source paths are absolute in the composed-stage save. Keep source assets in
  place; this is not a portable asset packager. For portable handoff use a
  deliberate asset collection workflow. Flattening does not embed textures.
- Layer mute and payload load choices are browsing/session state, preserved in
  `.blend`, not encoded as USD layer opinions. Composed Save As retains layer
  references regardless of muting; flatten uses the current composed state.
- Preview caches are stored under Blender's user data directory at
  `usd_stage_manager/cache`. They persist because USD animation/cache readers in
  saved `.blend` files may still require them. Copy needed caches when moving a
  `.blend` to another machine. Delete caches manually only when no saved files
  need them. Repeated refreshes accumulate cache files and may leave imported
  orphan data blocks; use Blender's orphan-data cleanup as appropriate.
- USD edits are not continuously synced to Blender objects. Refresh is explicit.
  Blender edits do not flow back into USD. Export Blender geometry to a separate
  USD file and reference or sublayer it into the stage.
- Generic scalar values can be edited at default time. Existing time samples
  still win at sampled times. Arrays, transforms, meshes, material networks and
  relationships are inspection-only in the prim inspector.
- Namespace rename/reparent, arbitrary edit targets, layer time-offset UI,
  Hydra delegates, LOP nodes and two-way scene synchronization are not included.
- Scene graph rebuilds are explicit (or triggered by search/edits); very large
  stages can take time. USD instance prototypes are not expanded in this tree.
- Tested on official Blender 5.2.2 Linux. macOS and Windows need platform testing.
  If a custom Blender build lacks `pxr`, the UI explains that and leaves native
  USD import/export available. The add-on does not modify Python packages.

## Validation

- 10 real OpenUSD backend tests: composition, source protection, metadata,
  variants, search, inactive prims, payloads, persistence, undo/redo, muting,
  validation rollback, scalar opinions and flattening.
- Blender 5.2.2 background smoke test: registration/unregistration, stage actions,
  structure idempotency/world transforms, preview replacement with selected
  preview objects, native import/export, and `.blend` save/reopen.
- Embedded-pane test: no new windows, repeat-open reuses the pane, and the pane
  survives saving/reopening the .blend. Verified in Blender 5.2.2 background mode;
  interactive appearance still needs testing on macOS.
- Blender extension manifest validation.

Source tests are in the repository's `tests/` directory. From the repository:

```sh
python -m unittest discover -s tests -v  # needs usd-core in this Python
blender --background --factory-startup --python-exit-code 1 --python tests/blender_smoke.py
blender --background --factory-startup --python-exit-code 1 --python tests/blender_dock.py
blender --command extension validate usd_stage_manager
```

Original source: https://github.com/SMUELDigital/BlenderAddon-USD-Asset-Manager
Blender builds: https://download.blender.org/release/Blender5.2/
Blender USD API source: https://github.com/blender/blender/blob/blender-v5.2-release/source/blender/editors/io/io_usd.cc
