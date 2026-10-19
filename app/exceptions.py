"""Errores de dominio. La API los traduce a respuestas HTTP en main.py."""


class RecursoNoEncontrado(Exception):
    pass


class ReglaDeNegocioInvalida(Exception):
    pass
