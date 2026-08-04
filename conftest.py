"""Marca la raiz del proyecto para pytest.

Su sola presencia hace que pytest agregue este directorio a ``sys.path``, de
modo que las pruebas puedan importar ``configuracion``, ``esquema_contrato`` y
el paquete ``generador`` sin necesidad de instalar el proyecto.
"""
