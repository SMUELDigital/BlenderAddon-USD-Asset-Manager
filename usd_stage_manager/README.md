# USD Stage Manager 2.2.0 — Blender 5.2

A Solaris-inspired scene graph and working-layer editor using Blender's bundled
OpenUSD. Tested in Blender 5.2.2 LTS on Linux; macOS/Windows interactive testing
is still needed.

## Installation

Disable the old USD Layers Panel. Install `USD_Stage_Manager_Blender52_v2.2.0.zip`
through Preferences → Add-ons → Install from Disk, then restart Blender.
Open **3D View → N → USD Stage → Open Embedded USD Stage**.
The stage docks below the viewport, without creating a floating window. Repeated
clicks reuse the pane. Resize the divider and save the .blend; reopen with Load UI
enabled to retain the layout. A viewport height of at least 420 pixels is needed.
The pane uses native Scene Properties panels; it is not a new compiled editor.

Wide panes show the prim tree, inspector and layers side by side. Narrow panes
stack the sections. The attribute inspector uses a scrollable list.

## Two separate data sources

**The USD tree displays the composed USD stage. It is not Blender's Outliner.**
A fresh stage contains `/World`; Blender's cube, camera and lights are not part
of that USD stage until exported and opened.

- **New / Open:** create or open a USD stage. Opening another stage requires
  enabling Replace current working stage in the file browser.
- **Export Blender Scene to USD:** exports Blender objects. By default, excludes
  managed USD preview objects, writes USD Preview Surface materials and textures,
  and opens the exported USD in the tree. Set Selected only deliberately; it may
  export just the camera if that is the only selected object. Export animation,
  world environment, preview inclusion and opening the export are explicit options.
- **Restore Previous USD Stage:** recovers the stage that was active before the
  most recent export-and-open. It swaps between those two stage snapshots.
- **Save USD Stage As:** saves USD edits from the tree, not Blender object edits.
- **Refresh Viewport:** imports a snapshot of the current USD stage into a managed
  preview collection. Refresh replaces that preview. Modeling edits on preview
  objects are not written back to USD and will be lost on refresh.

The active source filename is shown above the tree. There is no automatic
bidirectional sync. To bring Blender edits into USD, export again to a new file.
Source-layer filenames in the current stage are protected from overwrite.

## Stage editing

Search by prim path or type; matching ancestors remain visible. Expand/collapse
branches with triangles. Inspect attributes, relationships, variants and the prim
opinion stack. The eye authors visibility, the checkbox activation, and payload
controls load/unload. A hidden ancestor still hides its descendants.

Add Xform/Scope prims or compose references/payloads at new absolute prim paths.
Referenced assets need a defaultPrim. Add, reorder, mute or remove direct source
sublayers; nested composition can be inspected in Prim Composition. All authored
opinions belong to the strongest working layer. Source files are not edited.

Scalar default attribute values are editable; arrays, mesh topology, transforms,
relationships and material networks are inspection-only. Time samples take
precedence over default values when inspecting at an explicit USD time.

Use **Undo USD / Redo USD** for USD edits (32 entries). The .blend stores the
current working-layer text and mute/load choices, but not USD undo history.

## Validation and interchange

**Validate** runs the available official OpenUSD validators and composition checks.
Detailed results are written to Blender's `USD Validation Report` text block.
Exported Blender files also receive dependency checks. Counts vary by OpenUSD
version. Validation covers current variant selections and loaded content; it is
not exhaustive testing of every variant combination, animation sample, renderer
or application. A PASS means no errors were found by those checks, not universal
application support.

**Save As** writes the working layer and source references, using relative paths
where possible. Keep the referenced files and folder structure together. This
preserves variants/composition; it does not collect external dependencies.
**Flatten composition** bakes the evaluated composition into one layer, including
current variant choices. It does not embed textures.

**Publish Folder** creates a new folder named after the chosen filename, containing
`stage.usda` and copied local dependencies under `assets/`. Transfer the whole
folder. It validates the stage, requires all layers unmuted and payloads loaded,
and flattens the current variant choices. Existing publish folders are never
replaced. Missing, custom-resolver and package-relative assets are rejected rather
than silently publishing incomplete data. UDIM files are collected; resolver-driven
assets and complete multi-variant packaging are outside this publisher's scope.

The exporter requests standard USD Preview Surface materials, relative paths and
texture export. It omits add-on bookkeeping custom properties. Existing valid
ColorSpaceAPI metadata, schema types and transform hierarchies are preserved.
Xform parents around Mesh/Camera prims are valid USD and are not malformed duplicates.
USD validity does not imply that all applications implement all schemas, plugins,
color-management systems, textures, lights or rendering features identically.

## World assembly, lights and materials (2.2.0)

For exports with exactly one tagged World, the scene World and export-root
ancestors receive `kind = assembly` while retaining their Xform schema. Kind
appears separately in the prim inspector. The exporter creates a `materials`
Scope alongside cameras/extras/geo/lights, moves exported materials there and
updates USD bindings and shader connections through Usd.NamespaceEditor.

All exported prims carrying UsdLux.LightAPI outside the lights branch, including
the world environment DomeLight, are moved under that branch. Existing lights
already inside it retain their paths. Collisions use numbered names; no prim is
replaced. When necessary, a reset-stack placement chain preserves the old light
transform operations and time samples without matrix baking. Instanced lights
that cannot safely be moved fail organization explicitly. The original Blender
parenting is unchanged. Re-export is required to update previously saved USD.

This organization is limited to freshly exported, single-layer stages with one
unambiguous tagged World; opening/saving arbitrary USD assets does not reorganize
them. With no tagged World, use Organize Blender Scene for USD first. Multiple
tagged Worlds are not implicitly merged. The two World levels remain the export
root and Blender's tagged scene root. No object is automatically labeled component.

## Scope typing

The add-on's tagged `geo`, `lights`, `cameras` and `extras` organizational empties
export as standard **Scope** prims by default. This works in both the add-on's
export and Blender's native USD export while the add-on is enabled, including
existing tagged scenes created with 2.1.0. Mapping uses Blender's exported prim
map and stored role, not object names, so renaming a group is supported.

World and object transform parents remain Xforms. A category with non-identity
local transforms, sampled transforms, or a reset transform stack also remains an
Xform to preserve placement/animation. The add-on reports why it was retained.
Untagged empties and geometry/camera/light/material types are not retyped.

Scope is a non-transformable organizational schema, not a mandatory replacement
for every grouping Xform. USD `kind` (group/assembly/component/subcomponent) is
separate model-hierarchy metadata. This fix does not guess asset boundaries or
assign every object the kind component. “Actor” is not a core UsdGeom prim type.
The two World levels represent the export root and the scene's World object;
their paths are preserved for references and bindings.

## Blender scene organization

Organize Blender Scene for USD explicitly creates tagged World/geo/lights/cameras/
extras empties. Existing hierarchies and world transforms are kept. Preview objects
and linked-library objects are skipped. It is safe to run twice. No dependency-graph
handler continuously reparents objects. Blender's native File → Export → USD dialog
remains available for advanced native exporter options.

## Limits and persistence

- References/textures stay external in .blend snapshots and normal USD saves.
- Preview caches live in Blender's user data directory, `usd_stage_manager/cache`.
  Keep needed caches with saved .blend files that use animated USD/cache data;
  repeated refreshes accumulate files. Orphan data blocks can be cleaned in Blender.
- Mute/load choices are .blend browsing state, not authored USD layer opinions.
- No Hydra viewport, LOP node network, namespace rename/reparent, arbitrary edit
  targets, or two-way object sync is included.
- Stages with missing dependencies can be inspected and saved; portable publishing
  rejects unresolved data. Check the validation report before handing files off.
- Interactive UI appearance has not been rendered in this environment. Background
  tests verify docking, pane reuse, save/reopen, operators, export and validation.

## Tests

From the repository, with usd-core available for the standalone Python tests:

```sh
python -m unittest discover -s tests -v
blender --background --factory-startup --python-exit-code 1 --python tests/blender_smoke.py
blender --background --factory-startup --python-exit-code 1 --python tests/blender_dock.py
blender --background --factory-startup --python-exit-code 1 --python tests/blender_export.py
blender --command extension validate usd_stage_manager
```

Sources:
- https://github.com/SMUELDigital/BlenderAddon-USD-Asset-Manager
- https://openusd.org/release/toolset.html#usdchecker
- https://openusd.org/release/toolset.html#usdcat

Scope reference: https://openusd.org/release/api/class_usd_geom_scope.html
Model kinds: https://openusd.org/release/glossary.html#kind
