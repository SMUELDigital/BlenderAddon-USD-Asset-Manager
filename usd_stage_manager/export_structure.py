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
