from equitywise.config.settings import Settings


def test_capital_gains_method_defaults_to_inr_components():
    assert Settings(_env_file=None).capital_gains_calculation_method == "inr-components"


def test_capital_gains_method_can_be_configured_from_environment(monkeypatch):
    monkeypatch.setenv(
        "RSU_FA_CAPITAL_GAINS_CALCULATION_METHOD",
        "usd-gain-conversion",
    )

    assert (
        Settings(_env_file=None).capital_gains_calculation_method
        == "usd-gain-conversion"
    )
