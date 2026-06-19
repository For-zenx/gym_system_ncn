import argparse
import hashlib
import json
import sys
from datetime import date, timedelta

SECRET_KEY = "perfectline_super_secreto_para_firmar_licencias_2026"


def compute_signature(machine_id, nombre, expires_on):
    payload = f"{machine_id}|{nombre}|{expires_on}|{SECRET_KEY}"
    return hashlib.sha256(payload.encode()).hexdigest()


def generar_licencia(machine_id, nombre, expires_on, output_path="license.dat"):
    firma = compute_signature(machine_id, nombre, expires_on)
    licencia = {
        "machine_id": machine_id,
        "nombre": nombre,
        "expires_on": expires_on,
        "signature": firma,
    }

    with open(output_path, "w", encoding="utf-8") as handle:
        json.dump(licencia, handle, indent=4)

    print(f"Licencia generada exitosamente en: {output_path}")
    print(f"   Gimnasio: {nombre}")
    print(f"   Machine ID: {machine_id}")
    print(f"   Vence el: {expires_on}")


def _parse_args():
    parser = argparse.ArgumentParser(description="Generador de licencias NCN Gym")
    parser.add_argument("machine_id", nargs="?", help="Machine ID de la PC del gym")
    parser.add_argument("nombre", nargs="?", help="Nombre del gimnasio")
    parser.add_argument("output_path", nargs="?", default="license.dat", help="Ruta de salida")
    parser.add_argument("--expires", dest="expires_on", help="Fecha YYYY-MM-DD")
    parser.add_argument("--years", type=int, default=1, help="Anios de validez desde hoy (default: 1)")
    return parser.parse_args()


if __name__ == "__main__":
    print("--- Generador de Licencias NCN Gym ---")
    args = _parse_args()

    machine_id = args.machine_id or input("Introduce el Machine ID de la computadora: ").strip()
    nombre = args.nombre or input("Introduce el Nombre del gimnasio (ej. Gym Power): ").strip()
    output_path = args.output_path

    if not machine_id or not nombre:
        print("Datos incompletos.")
        sys.exit(1)

    if args.expires_on:
        expires_on = args.expires_on
    else:
        expires_on = (date.today() + timedelta(days=365 * args.years)).isoformat()

    generar_licencia(machine_id, nombre, expires_on, output_path)
