"""Límite de peticiones y caché en disco."""

from __future__ import annotations

import hashlib
import json
import threading
import time
from collections import deque
from pathlib import Path
from typing import Any


class LimitadorPeticiones:
    """Ventana deslizante: como máximo N peticiones por minuto."""

    def __init__(self, maximo_por_minuto: int) -> None:
        self.maximo_por_minuto = max(1, maximo_por_minuto)
        self._marcas: deque[float] = deque()
        self._candado = threading.Lock()

    def adquirir(self) -> None:
        with self._candado:
            ahora = time.monotonic()
            while self._marcas and ahora - self._marcas[0] >= 60:
                self._marcas.popleft()
            if len(self._marcas) >= self.maximo_por_minuto:
                espera = 60 - (ahora - self._marcas[0]) + 0.05
                time.sleep(max(espera, 0.05))
                ahora = time.monotonic()
                while self._marcas and ahora - self._marcas[0] >= 60:
                    self._marcas.popleft()
            self._marcas.append(time.monotonic())

    def estadisticas(self) -> dict[str, Any]:
        with self._candado:
            ahora = time.monotonic()
            while self._marcas and ahora - self._marcas[0] >= 60:
                self._marcas.popleft()
            return {
                "maximo_por_minuto": self.maximo_por_minuto,
                "usadas_ultimo_minuto": len(self._marcas),
            }


class CacheDisco:
    def __init__(self, raiz: str | Path) -> None:
        self.raiz = Path(raiz)
        self.raiz.mkdir(parents=True, exist_ok=True)
        self._candado = threading.Lock()

    def _ruta(self, clave: str) -> Path:
        resumen = hashlib.sha256(clave.encode()).hexdigest()
        return self.raiz / f"{resumen}.json"

    def obtener(self, clave: str) -> Any | None:
        ruta = self._ruta(clave)
        with self._candado:
            if not ruta.exists():
                return None
            try:
                carga = json.loads(ruta.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                return None
            if carga.get("caduca_en", 0) < time.time():
                ruta.unlink(missing_ok=True)
                return None
            return carga.get("datos")

    def guardar(self, clave: str, datos: Any, ttl_segundos: int) -> None:
        ruta = self._ruta(clave)
        carga = {
            "caduca_en": time.time() + max(1, ttl_segundos),
            "guardado_en": time.time(),
            "datos": datos,
        }
        with self._candado:
            ruta.write_text(json.dumps(carga, ensure_ascii=False), encoding="utf-8")

    def vaciar(self) -> int:
        eliminados = 0
        with self._candado:
            for ruta in self.raiz.glob("*.json"):
                ruta.unlink(missing_ok=True)
                eliminados += 1
        return eliminados

    def estadisticas(self) -> dict[str, Any]:
        archivos = list(self.raiz.glob("*.json"))
        return {"entradas": len(archivos), "ruta": str(self.raiz.resolve())}
