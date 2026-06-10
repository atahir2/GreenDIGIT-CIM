import pytest
from cloud_metrics.mapping.namespace_mapper import map_raw_to_unified, UnifiedMetric

@pytest.mark.parametrize(
    "raw_key, expected_name",
    [
        ("CPUUtilization", "cpu_usage"),
        ("MemoryAvailableMB",   "mem_free"),
    ],
)
def test_map_known_keys(raw_key, expected_name):
    result = map_raw_to_unified(raw_key, 123.4)
    assert isinstance(result, UnifiedMetric)
    assert result.name == expected_name
    assert result.tags == {}

def test_map_unknown_key():
    assert map_raw_to_unified("NO_SUCH_METRIC", 0.0) is None
