"""Esquema unico de los campos de un contrato.

Este modulo es la fuente de verdad compartida por el generador, el extractor y
el modulo de evaluacion: define que campos existen, como se llaman y de que tipo
es su valor canonico.

Los nombres estan alineados con el esquema del extractor de produccion, de modo
que lo que se valida sobre datos sinteticos se transfiera sin renombrar campos.
"""

from dataclasses import asdict, dataclass, fields


@dataclass(frozen=True)
class ContratoSintetico:
    """Valores canonicos de un contrato de arriendo vehicular sintetico.

    "Canonico" significa independiente del formato con que se imprima en el PDF:
    la fecha siempre en ISO ``YYYY-MM-DD``, el monto siempre como entero de pesos
    y la patente siempre sin separador (``BCDF12``). Cada plantilla decide despues
    como renderizar esos mismos valores, y esa divergencia es justamente lo que el
    extractor debe resolver.
    """

    # -- Vehiculo --
    ppu: str                    # patente unica, formato LLLLNN sin separador
    marca: str
    modelo: str
    ano: int

    # -- Arrendatario (persona juridica) --
    razon_social: str
    rut_empresa: str            # con puntos y guion: 99.123.456-7
    giro: str
    domicilio: str

    # -- Representante legal (persona natural) --
    nombre_representante: str
    rut_representante: str      # su cedula de identidad: en Chile es el mismo RUN

    # -- Condiciones economicas --
    fecha_inicio: str           # ISO YYYY-MM-DD
    fecha_termino: str          # ISO YYYY-MM-DD
    plazo_meses: int            # derivado de las dos fechas anteriores
    valor_cuota: int            # pesos chilenos, sin decimales
    numero_pagare: str

    def a_diccionario(self) -> dict:
        """Devuelve los campos como diccionario listo para serializar a JSON."""
        return asdict(self)


#: Nombres de los campos, en el orden en que se declaran arriba.
CAMPOS_CONTRATO = tuple(campo.name for campo in fields(ContratoSintetico))

#: Tipo canonico esperado de cada campo, usado por las pruebas y la evaluacion.
TIPOS_CAMPOS = {campo.name: campo.type for campo in fields(ContratoSintetico)}
