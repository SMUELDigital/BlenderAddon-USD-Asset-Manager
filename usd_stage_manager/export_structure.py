"""Type explicitly tagged organizational containers without changing transforms."""
from pxr import Gf, Usd, UsdGeom

SCOPE_ROLES = frozenset(('geo', 'lights', 'cameras', 'extras'))


def make_scope(prim):
    """Return a reason when retaining an Xform is required; otherwise author Scope.

    Only call for known organizational empties, never infer intent from a name.
    Animated operations and reset stacks remain Xforms even if currently identity.
    """
    if prim.GetTypeName() == 'Scope':
        return ''
    if prim.GetTypeName() != 'Xform' or prim.IsInstance() or prim.IsInstanceProxy():
        return 'not an editable Xform container'
    xf = UsdGeom.Xformable(prim)
    if xf.GetResetXformStack():
        return 'resets inherited transforms'
    attrs = [a for a in prim.GetAttributes() if a.GetName().startswith('xformOp:')]
    if any(a.GetNumTimeSamples() for a in attrs):
        return 'has sampled transforms'
    if not Gf.IsClose(xf.GetLocalTransformation(Usd.TimeCode.Default()), Gf.Matrix4d(1), 1e-12):
        return 'has a non-identity local transform'
    # On a freshly exported stage these properties belong to the writable root.
    for attr in attrs:
        prim.RemoveProperty(attr.GetName())
    prim.RemoveProperty('xformOpOrder')
    prim.SetTypeName('Scope')
    return ''


def _unique_path(stage, parent, name):
    path = parent.AppendChild(name)
    index = 1
    while stage.GetPrimAtPath(path):
        path = parent.AppendChild(name + '_' + str(index))
        index += 1
    return path


def _move(stage, source, target):
    editor = Usd.NamespaceEditor(stage)
    if not editor.MovePrimAtPath(source, target):
        raise ValueError('Cannot queue USD move: ' + str(source))
    result = editor.CanApplyEdits()
    if not result:
        raise ValueError('Cannot move USD prim: ' + str(result))
    if not editor.ApplyEdits():
        raise ValueError('Failed USD move: ' + str(source))


def _light_destination(stage, branch, lights):
    """Retain the old transform chain exactly when reparenting across transforms.

    An extra reset-stack chain is needed only when either ancestry has transform
    opinions. Copy individual operations/samples, avoiding matrix baking and its
    interpolation changes. The moved light's own operations remain untouched.
    """
    from pxr import Sdf
    ancestors = []
    p = branch.GetParent()
    while p and not p.IsPseudoRoot():
        ancestors.append(p)
        p = p.GetParent()
    old_transforms = any(UsdGeom.Xformable(p) and (
        UsdGeom.Xformable(p).GetOrderedXformOps() or UsdGeom.Xformable(p).GetResetXformStack())
        for p in ancestors)
    new_transforms = False
    p = stage.GetPrimAtPath(lights)
    while p and not p.IsPseudoRoot():
        xf = UsdGeom.Xformable(p)
        if xf and (xf.GetOrderedXformOps() or xf.GetResetXformStack()):
            new_transforms = True
        p = p.GetParent()
    if not old_transforms and not new_transforms:
        return _unique_path(stage, lights, branch.GetName())
    root = _unique_path(stage, lights, branch.GetName() + '_placement')
    UsdGeom.Xform.Define(stage, root).SetResetXformStack(True)
    target = root
    layer = stage.GetRootLayer()
    for ancestor in reversed(ancestors):
        xf = UsdGeom.Xformable(ancestor)
        if not xf or not (xf.GetOrderedXformOps() or xf.GetResetXformStack()):
            continue
        target = target.AppendChild(ancestor.GetName())
        UsdGeom.Xform.Define(stage, target)
        for attr in ancestor.GetAttributes():
            name = attr.GetName()
            if name == 'xformOpOrder' or name.startswith('xformOp:'):
                source = attr.GetPath()
                if layer.GetPropertyAtPath(source):
                    if not Sdf.CopySpec(layer, source, layer, target.AppendProperty(name)):
                        raise ValueError('Cannot preserve light transform: ' + str(source))
    return target.AppendChild(branch.GetName())


def organize_export(stage, world_path, category_paths):
    """Organize a fresh, single-layer Blender export; never edit source assets."""
    from pxr import Kind, UsdLux, UsdShade
    world = stage.GetPrimAtPath(world_path)
    if not world:
        raise ValueError('Missing exported World')
    # A model needs a continuous chain of group-model ancestors. Assembly is a
    # group kind and leaves Xform/schema identity unchanged.
    p = world
    while p and not p.IsPseudoRoot():
        Usd.ModelAPI(p).SetKind(Kind.Tokens.assembly)
        p = p.GetParent()
    for role in ('cameras', 'extras', 'geo', 'lights', 'materials'):
        if role not in category_paths:
            candidate = world_path.AppendChild(role)
            existing = stage.GetPrimAtPath(candidate)
            if existing and existing.GetTypeName() != 'Scope':
                candidate = _unique_path(stage, world_path, role)
            UsdGeom.Scope.Define(stage, candidate)
            category_paths[role] = candidate
    materials = category_paths['materials']
    # Move entire native material scopes when possible, retaining all shader
    # paths relative to their materials. NamespaceEditor updates bindings/connections.
    sources = [p.GetPath() for p in stage.Traverse() if p.IsA(UsdShade.Material)
               and not p.GetPath().HasPrefix(materials)]
    for source in sources:
        prim = stage.GetPrimAtPath(source)
        old_parent = prim.GetParent()
        old_parent_path = old_parent.GetPath()
        _move(stage, source, _unique_path(stage, materials, prim.GetName()))
        if old_parent.GetTypeName() == 'Scope' and old_parent.GetName() == '_materials' and not old_parent.GetChildren():
            stage.RemovePrim(old_parent_path)
    lights = category_paths['lights']
    paths = [p.GetPath() for p in stage.Traverse() if p.HasAPI(UsdLux.LightAPI)
             and not p.GetPath().HasPrefix(lights)]
    for path in paths:
        prim = stage.GetPrimAtPath(path)
        if not prim:
            continue
        branch = prim
        parent = branch.GetParent()
        while (parent and parent.GetTypeName() == 'Xform' and len(parent.GetChildren()) == 1
               and parent.GetPath() != world_path
               and not world_path.HasPrefix(parent.GetPath())
               and parent.GetPath() not in category_paths.values()):
            branch, parent = parent, parent.GetParent()
        if branch.IsInstance() or branch.IsInstanceProxy():
            raise ValueError('Cannot reorganize an instanced light: ' + str(branch.GetPath()))
        destination = _light_destination(stage, branch, lights)
        _move(stage, branch.GetPath(), destination)
    return category_paths
