"""OpenUSD validation and dependency inspection. No Blender dependency."""
from collections import Counter
from pxr import Usd, UsdGeom, UsdShade, UsdUtils, Sdf


def audit_file(path):
    stage = Usd.Stage.Open(str(path), load=Usd.Stage.LoadAll)
    if not stage:
        raise ValueError('Cannot open USD stage: ' + str(path))
    return audit_stage(stage, str(path))


def audit_stage(stage, dependency_path=None):
    report = {'usd_version': '.'.join(map(str, Usd.GetVersion())),
              'scope': 'Current variant selections; all loaded prims. Not an all-application certification.',
              'errors': [], 'warnings': [], 'validators': [], 'dependencies': [],
              'metadata': {'defaultPrim': str(stage.GetDefaultPrim().GetPath()) if stage.GetDefaultPrim() else '',
                           'upAxis': str(UsdGeom.GetStageUpAxis(stage)),
                           'metersPerUnit': UsdGeom.GetStageMetersPerUnit(stage),
                           'timeCodesPerSecond': stage.GetTimeCodesPerSecond(),
                           'framesPerSecond': stage.GetFramesPerSecond()},
              'prim_types': dict(Counter(p.GetTypeName() or 'Untyped' for p in stage.TraverseAll()))}
    for error in stage.GetCompositionErrors():
        report['errors'].append(str(error))
    if not stage.GetDefaultPrim():
        report['warnings'].append('No defaultPrim: references must specify a prim path.')
    for key in ('upAxis', 'metersPerUnit'):
        if not stage.HasAuthoredMetadata(key):
            report['warnings'].append('Stage metadata is not explicitly authored: ' + key)
    try:
        from pxr import UsdValidation
        registry = UsdValidation.ValidationRegistry()
        validators = registry.GetOrLoadAllValidators()
        report['validators'] = [str(v.GetMetadata().name) for v in validators]
        context = UsdValidation.ValidationContext(validators)
        for error in context.Validate(stage):
            bucket = 'errors' if error.GetType() == UsdValidation.ValidationErrorType.Error else 'warnings'
            report[bucket].append(str(error.GetIdentifier()) + ': ' + error.GetMessage())
    except (ImportError, AttributeError) as exc:
        # Older OpenUSD distributions do not expose the new validation framework.
        if dependency_path and hasattr(UsdUtils, 'ComplianceChecker'):
            checker = UsdUtils.ComplianceChecker(arkit=False, skipARKitRootLayerCheck=True)
            checker.CheckCompliance(dependency_path)
            report['validators'] = ['UsdUtils.ComplianceChecker (legacy)']
            report['errors'].extend(map(str, checker.GetErrors()))
            report['errors'].extend(map(str, checker.GetFailedChecks()))
            report['warnings'].extend(map(str, checker.GetWarnings()))
        else:
            report['warnings'].append('Official validator API unavailable: ' + str(exc))
    if dependency_path:
        layers, assets, unresolved = UsdUtils.ComputeAllDependencies(Sdf.AssetPath(dependency_path))
        report['dependencies'] = sorted(set([l.realPath for l in layers if l.realPath] + list(assets)))
        report['errors'].extend('Unresolved dependency: ' + str(p) for p in unresolved)
    for prim in stage.TraverseAll():
        if prim.IsA(UsdShade.Shader):
            shader_id = UsdShade.Shader(prim).GetIdAttr().Get()
            if shader_id and shader_id not in ('UsdPreviewSurface', 'UsdUVTexture', 'UsdTransform2d') and not shader_id.startswith('UsdPrimvarReader_'):
                report['warnings'].append('Renderer/plugin-specific shader may require extra support: ' + str(shader_id))
    report['errors'] = sorted(set(report['errors']))
    report['warnings'] = sorted(set(report['warnings']))
    report['passed'] = not report['errors']
    return report
