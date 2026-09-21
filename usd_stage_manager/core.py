"""USD stage operations, independent of Blender. Rewrite of SMUELDigital's manager."""
import json
import os
from contextlib import contextmanager
from pathlib import Path

try:
    from pxr import Sdf, Usd, UsdGeom, UsdShade, Tf
    USD_ERROR = ''
except ImportError as exc:
    Sdf = Usd = UsdGeom = UsdShade = Tf = None
    USD_ERROR = str(exc)


def require_usd():
    if Usd is None:
        raise RuntimeError('This Blender build does not provide the OpenUSD Python modules (pxr). '
                           'Use a Blender build with USD Python support. Native USD import/export is still available.')


def identifier(value):
    require_usd()
    return Tf.MakeValidIdentifier(value.strip() or 'World')


def prim_path(value):
    require_usd()
    path = Sdf.Path(value)
    if not path.IsAbsolutePath() or not path.IsPrimPath():
        raise ValueError('Enter an absolute USD prim path, for example /World/Asset.')
    return path


class Session:
    """All opinions belong to an anonymous working layer; source layers are never saved."""
    def __init__(self, source=None):
        require_usd()
        self.root = Sdf.Layer.CreateAnonymous('working.usda')
        self.stage = Usd.Stage.Open(self.root)
        self.undo_stack = []
        self.redo_stack = []
        self.unloaded = set()
        self.revision = 0
        if source:
            path = self.checked_file(source)
            self.root.subLayerPaths = [path]
            source_stage = Usd.Stage.Open(path, load=Usd.Stage.LoadNone)
            for key in ('defaultPrim', 'upAxis', 'metersPerUnit', 'startTimeCode',
                        'endTimeCode', 'timeCodesPerSecond', 'framesPerSecond'):
                if source_stage.HasAuthoredMetadata(key):
                    self.stage.SetMetadata(key, source_stage.GetMetadata(key))
        else:
            root = UsdGeom.Xform.Define(self.stage, '/World').GetPrim()
            self.stage.SetDefaultPrim(root)
            UsdGeom.SetStageUpAxis(self.stage, UsdGeom.Tokens.z)
            UsdGeom.SetStageMetersPerUnit(self.stage, 1.0)

    @staticmethod
    def checked_file(path):
        path = os.path.abspath(os.path.expanduser(path))
        if not os.path.isfile(path):
            raise ValueError('USD file does not exist: ' + path)
        if not Sdf.Layer.FindOrOpen(path):
            raise ValueError('Cannot read USD layer: ' + path)
        return path

    def snapshot(self):
        return json.dumps({'version': 1, 'layer': self.root.ExportToString(),
                           'muted': list(self.stage.GetMutedLayers()),
                           'unloaded': sorted(self.unloaded)})

    def _restore(self, text):
        data = json.loads(text)
        if data.get('version') != 1:
            raise ValueError('Unsupported saved stage version')
        if not self.root.ImportFromString(data['layer']):
            raise ValueError('Cannot restore working USD layer')
        current = set(self.stage.GetMutedLayers())
        desired = set(data.get('muted', []))
        self.stage.MuteAndUnmuteLayers(sorted(desired - current), sorted(current - desired))
        self.stage.Load()
        self.unloaded = set(data.get('unloaded', []))
        for path in sorted(self.unloaded):
            if self.stage.GetPrimAtPath(path):
                self.stage.Unload(path)
        self.stage.SetEditTarget(self.root)
        self.revision += 1

    @classmethod
    def from_snapshot(cls, text):
        obj = cls()
        obj._restore(text)
        return obj

    @contextmanager
    def change(self):
        before = self.snapshot()
        try:
            yield
        except Exception:
            self._restore(before)
            raise
        if self.snapshot() != before:
            self.undo_stack.append(before)
            self.undo_stack = self.undo_stack[-32:]
            self.redo_stack.clear()
            self.revision += 1

    def undo(self):
        if not self.undo_stack:
            return
        state = self.undo_stack.pop()
        self.redo_stack.append(self.snapshot())
        self._restore(state)

    def redo(self):
        if not self.redo_stack:
            return
        state = self.redo_stack.pop()
        self.undo_stack.append(self.snapshot())
        self._restore(state)

    def prim(self, path):
        prim = self.stage.GetPrimAtPath(prim_path(path))
        if not prim:
            raise ValueError('Prim no longer exists: ' + path)
        return prim

    def rows(self, search='', collapsed=()):
        # TraverseAll includes inactive prims and unloaded payload roots.
        prims = list(self.stage.TraverseAll())
        query = search.casefold().strip()
        matched = set()
        if query:
            for p in prims:
                if query in str(p.GetPath()).casefold() or query in p.GetTypeName().casefold():
                    matched.update(str(x) for x in p.GetPath().GetPrefixes())
        collapsed = {Sdf.Path(p) for p in collapsed}
        for p in prims:
            path = p.GetPath()
            if query and str(path) not in matched:
                continue
            if not query and any(parent != path and path.HasPrefix(parent) for parent in collapsed):
                continue
            imageable = UsdGeom.Imageable(p)
            yield {'path': str(path), 'name': p.GetName(), 'depth': path.pathElementCount - 1,
                   'type': p.GetTypeName() or 'Untyped', 'active': p.IsActive(),
                   'children': bool(p.GetAllChildren()), 'payload': p.HasPayload(),
                   'loaded': p.IsLoaded(), 'instance': p.IsInstance(),
                   'visible': not imageable or imageable.ComputeVisibility() != UsdGeom.Tokens.invisible}

    def add_layer(self, path):
        path = self.checked_file(path)
        if path in self.root.subLayerPaths:
            raise ValueError('This layer is already in the stack')
        with self.change():
            self.root.subLayerPaths.insert(0, path)

    def remove_layer(self, index):
        with self.change():
            paths = list(self.root.subLayerPaths)
            path = paths.pop(index)
            self.stage.UnmuteLayer(path)
            self.root.subLayerPaths = paths

    def move_layer(self, index, delta):
        paths = list(self.root.subLayerPaths)
        target = index + delta
        if not 0 <= index < len(paths) or not 0 <= target < len(paths):
            return
        with self.change():
            offsets = list(self.root.subLayerOffsets)
            paths[index], paths[target] = paths[target], paths[index]
            offsets[index], offsets[target] = offsets[target], offsets[index]
            self.root.subLayerPaths = paths
            for i, offset in enumerate(offsets):
                self.root.subLayerOffsets[i] = offset

    def mute_layer(self, path):
        with self.change():
            if self.stage.IsLayerMuted(path):
                self.stage.UnmuteLayer(path)
            else:
                self.stage.MuteLayer(path)

    def set_visibility(self, path, visible):
        with self.change():
            prim = UsdGeom.Imageable(self.prim(path))
            if not prim:
                raise ValueError('This prim is not imageable')
            prim.CreateVisibilityAttr().Set(UsdGeom.Tokens.inherited if visible else UsdGeom.Tokens.invisible)

    def set_active(self, path, active):
        with self.change():
            self.prim(path).SetActive(active)

    def set_loaded(self, path, loaded):
        with self.change():
            if not self.prim(path).HasPayload():
                raise ValueError('Selected prim has no payload')
            if loaded:
                self.stage.Load(path)
                self.unloaded = {p for p in self.unloaded if not Sdf.Path(p).HasPrefix(Sdf.Path(path))}
            else:
                self.stage.Unload(path)
                self.unloaded.add(path)

    def set_variant(self, path, name, value):
        with self.change():
            variant = self.prim(path).GetVariantSet(name)
            if value not in variant.GetVariantNames():
                raise ValueError('Variant is not present on this prim')
            if not variant.SetVariantSelection(value):
                raise ValueError('Could not author variant selection')

    def define(self, path, type_name='Xform'):
        path = prim_path(path)
        if self.stage.GetPrimAtPath(path):
            raise ValueError('A prim already exists at this path')
        with self.change():
            self.stage.DefinePrim(path, type_name)

    def add_asset(self, file, path, payload=False):
        file = self.checked_file(file)
        path = prim_path(path)
        if self.stage.GetPrimAtPath(path):
            raise ValueError('Choose a new prim path to avoid replacing an existing asset')
        asset = Usd.Stage.Open(file, load=Usd.Stage.LoadNone)
        if not asset.GetDefaultPrim():
            raise ValueError('Asset needs a defaultPrim. Set one in the asset before referencing it.')
        with self.change():
            p = self.stage.DefinePrim(path, 'Xform')
            arc = p.GetPayloads() if payload else p.GetReferences()
            if not (arc.AddPayload(file) if payload else arc.AddReference(file)):
                raise ValueError('Could not add composition arc')

    def set_purpose(self, path, value):
        if value not in ('default', 'render', 'proxy', 'guide'):
            raise ValueError('Invalid purpose')
        with self.change():
            p = UsdGeom.Imageable(self.prim(path))
            if not p:
                raise ValueError('This prim does not support purpose')
            p.CreatePurposeAttr().Set(value)

    def set_default(self, path):
        p = self.prim(path)
        if p.GetPath().GetParentPath() != Sdf.Path.absoluteRootPath:
            raise ValueError('The default prim must be a root prim')
        with self.change():
            self.stage.SetDefaultPrim(p)

    def clear_opinions(self, path):
        with self.change():
            spec = self.root.GetPrimAtPath(prim_path(path))
            if not spec:
                raise ValueError('No working-layer opinions on this prim')
            edits = Sdf.BatchNamespaceEdit()
            edits.Add(spec.path, Sdf.Path.emptyPath)
            if not self.root.Apply(edits):
                raise ValueError('Could not clear working-layer opinions')

    def set_scalar(self, path, name, text):
        with self.change():
            attr = self.prim(path).GetAttribute(name)
            if not attr:
                raise ValueError('Attribute no longer exists')
            kind = str(attr.GetTypeName())
            if kind in ('string', 'token'):
                value = text
            elif kind == 'bool':
                if text.lower() not in ('true', 'false'):
                    raise ValueError('Use true or false')
                value = text.lower() == 'true'
            elif kind in ('int', 'int64', 'uint', 'uint64'):
                value = int(text)
                if kind.startswith('u') and value < 0:
                    raise ValueError('Unsigned values cannot be negative')
            elif kind in ('float', 'double', 'half'):
                value = float(text)
            else:
                raise ValueError('Only scalar strings, tokens, booleans and numbers are editable here')
            if not attr.Set(value, Usd.TimeCode.Default()):
                raise ValueError('USD rejected this value')

    def save(self, path, flatten=False):
        path = os.path.abspath(path)
        if Path(path).suffix.lower() not in ('.usd', '.usda', '.usdc'):
            raise ValueError('Save as .usd, .usda or .usdc')
        sources = {os.path.realpath(layer.realPath) for layer in self.stage.GetUsedLayers() if layer.realPath}
        sources.update(os.path.realpath(p) for p in self.root.subLayerPaths)
        if os.path.realpath(path) in sources:
            raise ValueError('Choose a new filename; source layers are protected from overwrite')
        layer = self.stage.Flatten() if flatten else self.root
        if not layer.Export(path):
            raise RuntimeError('USD export failed')
        return path

    def inspect(self, path, frame=None):
        p = self.prim(path)
        time = Usd.TimeCode.Default() if frame is None else Usd.TimeCode(frame)
        attrs = []
        for a in p.GetAttributes():
            value = a.Get(time)
            # Avoid printing entire geometry arrays in the UI.
            if a.GetTypeName().isArray:
                value = '<array: %s elements>' % (len(value) if value is not None else 0)
            attrs.append((a.GetName(), str(a.GetTypeName()), str(value)[:240], a.GetNumTimeSamples()))
        return {'attributes': attrs,
                'relationships': [(r.GetName(), ', '.join(str(t) for t in r.GetTargets())) for r in p.GetRelationships()],
                'variants': [(n, p.GetVariantSet(n).GetVariantSelection(), p.GetVariantSet(n).GetVariantNames())
                             for n in p.GetVariantSets().GetNames()],
                'stack': [(s.layer.identifier, str(s.path)) for s in p.GetPrimStack()]}
