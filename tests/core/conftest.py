# Minimal 1x1 JPEG as data URL for enrollment / re-enrollment POST tests.
FAKE_PHOTO_B64 = (
    "data:image/jpeg;base64,"
    "/9j/4AAQSkZJRgABAQEASABIAAD/2wBDAAgGBgcGBQgHBwcJCQgKDBQNDAsLDBkSEw8UHRof"
    "Hh0aHBwgJC4nICIsIxwcKDcpLDAxNDQ0Hyc5PTgyPC4zNDL/2wBDAQkJCQwLDBgNDRgyIRwh"
    "MjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjL/wAAR"
    "CAABAAEDASIAAhEBAxEB/8QAFQABAQAAAAAAAAAAAAAAAAAAAAn/xAAUEAEAAAAAAAAAAAAAAAAA"
    "AAAA/8QAFQEBAQAAAAAAAAAAAAAAAAAAAAX/xAAUEQEAAAAAAAAAAAAAAAAAAAAA/9oADAMB"
    "AAIRAxEAPwCwAA8A/9k="
)


def build_enrollment_post(**overrides):
    data = {
        "nombre": "Nuevo Afiliado Test",
        "cedula_prefix": "V-",
        "cedula_numero": "87654321",
        "telefono": "",
        "fecha_nacimiento": "",
        "sexo": "",
        "foto_frente_base64": FAKE_PHOTO_B64,
        "terms_accepted": "1",
    }
    data.update(overrides)
    return data
