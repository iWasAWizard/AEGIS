from hypothesis import given, strategies as st
from aegis.tools.primitives.chaos import random_string, inject_noise
from aegis.tools.primitives.chaos import RandomStringInput, InjectNoiseInput


@given(st.integers(min_value=1, max_value=100))
def test_random_string_length(length):
    result = random_string(RandomStringInput(length=length))
    assert isinstance(result, str)
    assert len(result) == length


@given(st.text(min_size=1, max_size=100))
def test_inject_noise_string_survives(input_text):
    result = inject_noise(InjectNoiseInput(data=input_text, noise_level="medium"))
    assert isinstance(result, str)
    assert len(result) >= len(input_text) - 1  # slight reductions ok


@given(
    st.dictionaries(
        keys=st.text(min_size=1, max_size=10), values=st.text(), max_size=10
    )
)
def test_inject_noise_dict_structure(input_dict):
    result = inject_noise(InjectNoiseInput(data=input_dict, noise_level="high"))
    assert isinstance(result, dict)
    assert len(result) >= len(input_dict)
