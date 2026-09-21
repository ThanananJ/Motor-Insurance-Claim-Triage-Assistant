import pytest

from src.config import AppConfig, ConfigurationError


def test_config_reads_ollama_environment():
    config = AppConfig.from_env(
        {
            "LLM_PROVIDER": "ollama",
            "OLLAMA_BASE_URL": "http://ollama.test:11434",
            "OLLAMA_MODEL": "configured-model",
            "OLLAMA_TIMEOUT_SECONDS": "12.5",
            "OLLAMA_NUM_CTX": "32768",
            "OLLAMA_RESERVED_OUTPUT_TOKENS": "256",
            "PROMPT_TOKEN_WARNING_PERCENT": "70",
            "PROMPT_TOKEN_CRITICAL_PERCENT": "85",
        }
    )
    assert config.llm_provider == "ollama"
    assert config.ollama_base_url == "http://ollama.test:11434"
    assert config.ollama_model == "configured-model"
    assert config.ollama_timeout_seconds == 12.5
    assert config.ollama_num_ctx == 32768
    assert config.reserved_output_tokens == 256
    assert config.prompt_token_warning_percent == 70
    assert config.prompt_token_critical_percent == 85


def test_missing_model_is_not_silently_defaulted():
    config = AppConfig.from_env({"LLM_PROVIDER": "ollama", "OLLAMA_MODEL": ""})
    assert config.ollama_model is None
    with pytest.raises(ConfigurationError, match="OLLAMA_MODEL is not configured"):
        config.require_ollama_model()


@pytest.mark.parametrize("timeout", ["not-a-number", "0", "-1"])
def test_invalid_timeout_is_rejected(timeout):
    with pytest.raises(ConfigurationError):
        AppConfig.from_env({"OLLAMA_TIMEOUT_SECONDS": timeout})


@pytest.mark.parametrize(
    "settings",
    [
        {"OLLAMA_NUM_CTX": "256", "OLLAMA_RESERVED_OUTPUT_TOKENS": "256"},
        {"OLLAMA_NUM_CTX": "invalid"},
        {"PROMPT_TOKEN_WARNING_PERCENT": "90", "PROMPT_TOKEN_CRITICAL_PERCENT": "85"},
    ],
)
def test_invalid_prompt_capacity_configuration_is_rejected(settings):
    with pytest.raises(ConfigurationError):
        AppConfig.from_env(settings)
