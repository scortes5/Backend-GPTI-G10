"""Errores de dominio. La API los traduce a respuestas HTTP en main.py."""


class RecursoNoEncontrado(Exception):
    pass


class ReglaDeNegocioInvalida(Exception):
    pass


class ServicioExternoNoDisponible(Exception):
    pass


class CredencialesInvalidas(Exception):
    pass


class AccesoDenegado(Exception):
    pass


class DemasiadosIntentos(Exception):
    pass
