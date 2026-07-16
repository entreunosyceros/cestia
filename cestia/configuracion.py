from functools import lru_cache

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Configuracion(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    url_base_mercadona: str = "https://tienda.mercadona.es/api"
    almacen_mercadona: str = "mad1"
    idioma_mercadona: str = "es"

    algolia_id_aplicacion: str = "7UZJKL1DJ0"
    algolia_clave_api: str = "9d8f2e39e90df472b4f2e559a116fe17"
    algolia_prefijo_indice: str = "products_prod"

    directorio_cache: str = ".cache"
    ttl_cache_categorias: int = 3600
    ttl_cache_productos: int = 1800
    ttl_cache_busqueda: int = 900

    limite_peticiones_por_minuto: int = 30
    timeout_http: float = 20.0
    agente_usuario: str = (
        "Mozilla/5.0 (compatible; CestIA/0.2; +uso-personal)"
    )

    # Compatibilidad con nombres antiguos del .env
    mercadona_warehouse: str | None = None
    mercadona_lang: str | None = None
    algolia_app_id: str | None = None
    algolia_api_key: str | None = None
    cache_dir: str | None = None
    rate_limit_per_minute: int | None = None

    @model_validator(mode="after")
    def aplicar_alias_env(self) -> "Configuracion":
        if self.mercadona_warehouse:
            self.almacen_mercadona = self.mercadona_warehouse
        if self.mercadona_lang:
            self.idioma_mercadona = self.mercadona_lang
        if self.algolia_app_id:
            self.algolia_id_aplicacion = self.algolia_app_id
        if self.algolia_api_key:
            self.algolia_clave_api = self.algolia_api_key
        if self.cache_dir:
            self.directorio_cache = self.cache_dir
        if self.rate_limit_per_minute:
            self.limite_peticiones_por_minuto = self.rate_limit_per_minute
        return self

    @property
    def indice_algolia(self) -> str:
        return (
            f"{self.algolia_prefijo_indice}_"
            f"{self.almacen_mercadona}_{self.idioma_mercadona}"
        )

    @property
    def url_algolia(self) -> str:
        host = f"{self.algolia_id_aplicacion.lower()}-dsn.algolia.net"
        return f"https://{host}/1/indexes/{self.indice_algolia}/query"


@lru_cache
def obtener_configuracion() -> Configuracion:
    return Configuracion()
