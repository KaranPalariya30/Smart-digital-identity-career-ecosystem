import json
import os
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    rpc_url: str = "http://127.0.0.1:8545"
    contract_address: str = ""
    deployment_artifact_path: str = "../../blockchain/deployments/localhost-deployment.json"
    issuer_private_key: str = ""
    database_url: str = "postgresql://postgres:postgres@localhost:5432/career_ecosystem"
    frontend_verify_base_url: str = "http://localhost:5173/verify"


@lru_cache
def get_settings() -> Settings:
    return Settings()


def load_contract_abi(settings: Settings) -> tuple[str, list]:
    """Resolve the contract address and ABI.

    Prefers CONTRACT_ADDRESS from the environment if set, but always reads
    the ABI (and falls back to the address) from the deployment artifact
    written by `blockchain/scripts/deploy.js`, so the service never has to
    hardcode the ABI by hand.
    """
    artifact_path = os.path.join(
        os.path.dirname(__file__), "..", settings.deployment_artifact_path
    )
    artifact_path = os.path.abspath(artifact_path)

    if not os.path.exists(artifact_path):
        raise FileNotFoundError(
            f"Deployment artifact not found at {artifact_path}. Run "
            f"'npm run deploy:localhost' in blockchain/ first."
        )

    with open(artifact_path) as f:
        deployment = json.load(f)

    address = settings.contract_address or deployment["address"]
    abi = deployment["abi"]
    return address, abi
