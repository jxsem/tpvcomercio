import logging

LOG_FORMAT = "%(asctime)s %(levelname)s %(name)s %(message)s"


def configure_logging() -> None:
    """Formato único con fecha y nivel para todos los logs de la aplicación.

    Regla del proyecto: nunca registrar contraseñas, tokens ni secretos. Por eso
    los logs de negocio llevan solo identificadores (user_id, product_id...).
    """
    logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)
