"""Environment configuration.

Pick an environment with `--env <name>` or TOOLSHOP_ENV. Individual URLs can be
overridden with TOOLSHOP_BASE_URL / TOOLSHOP_API_URL (e.g. for a new staging env).
Admin credentials come only from TOOLSHOP_ADMIN_EMAIL / TOOLSHOP_ADMIN_PASSWORD
(GitHub Actions secrets in CI, a local .env file otherwise), never from the repo.
"""
from pydantic import SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# name -> (web UI url, REST API url)
ENVIRONMENTS: dict[str, tuple[str, str]] = {
    "prod": ("https://practicesoftwaretesting.com", "https://api.practicesoftwaretesting.com"),
    "with-bugs": (
        "https://with-bugs.practicesoftwaretesting.com",
        "https://api-with-bugs.practicesoftwaretesting.com",
    ),
}


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="TOOLSHOP_", env_file=".env", extra="ignore")

    env: str = "prod"
    base_url: str | None = None
    api_url: str | None = None
    admin_email: str | None = None
    admin_password: SecretStr | None = None
    request_timeout: float = 15.0

    @model_validator(mode="after")
    def _fill_urls(self) -> "Settings":
        if self.env not in ENVIRONMENTS and not (self.base_url and self.api_url):
            raise ValueError(f"Unknown env '{self.env}'. Known: {sorted(ENVIRONMENTS)}")
        default_ui, default_api = ENVIRONMENTS.get(self.env, (None, None))
        self.base_url = (self.base_url or default_ui).rstrip("/")
        self.api_url = (self.api_url or default_api).rstrip("/")
        return self
