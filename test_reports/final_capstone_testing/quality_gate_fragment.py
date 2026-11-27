"""Test-only lowering of analytics.analyze's final quality classification.
Source predicates: len(passed)==2; truth value of passed. Upstream validators
remain actual production calls in the test matrix. This is NOT a new algorithm.
"""
def quality_gate_classification(reliable, gaze_usable):
    passed = [name for name, ok in (('suara', reliable), ('tatapan', gaze_usable)) if ok]
    if len(passed) == 2:
        quality = 'layak'
    else:
        if passed:
            quality = 'parsial'
        else:
            quality = 'tidak_cukup'
    return quality
