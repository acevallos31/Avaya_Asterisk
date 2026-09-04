#!/usr/bin/env python3
"""Build sanitized JSON and PDF reports from Test 53 fleet-audit output.

No third-party dependencies are required. The input log is already sanitized by
avaya-j129-prod-validation; this exporter never reads SIP passwords or Asterisk
secrets.
"""

import argparse
import datetime as dt
import json
import os
import shlex
import textwrap


def parse_kv(line):
    data = {}
    try:
        parts = shlex.split(line, posix=True)
    except ValueError:
        parts = line.split()
    for token in parts[1:]:
        if "=" in token:
            key, value = token.split("=", 1)
            data[key] = value
    return data


def parse_log(path):
    endpoints = []
    manufacturers = []
    summary = {}
    schema = None
    scope = None

    with open(path, "r", encoding="utf-8", errors="replace") as fh:
        for raw in fh:
            line = raw.rstrip("\n")
            if line.startswith("J129-PROD-FLEET-SCHEMA="):
                schema = line.split("=", 1)[1]
            elif line.startswith("J129-PROD-FLEET-SCOPE="):
                scope = line.split("=", 1)[1]
            elif line.startswith("MANUFACTURER "):
                manufacturers.append(parse_kv(line))
            elif line.startswith("AVAYA-ENDPOINT "):
                endpoints.append(parse_kv(line))
            elif line.startswith("J129-PROD-FLEET-SUMMARY "):
                summary = parse_kv(line)

    return {
        "report": "Ceiba - Avaya Fleet Audit",
        "generated_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "schema": schema,
        "scope": scope,
        "summary": summary,
        "manufacturers": manufacturers,
        "endpoints": endpoints,
        "security": {
            "sanitized": True,
            "sip_passwords_included": False,
            "asterisk_secrets_included": False,
            "credential_results_only": True,
        },
    }


def write_json(report, path):
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(report, fh, ensure_ascii=False, indent=2, sort_keys=True)
        fh.write("\n")


def safe(value, default="NONE"):
    value = str(value or default)
    return value.replace("\\ ", " ")


def report_lines(report):
    s = report.get("summary", {})
    lines = [
        "CEIBA - AVAYA FLEET AUDIT",
        "",
        "Auditoria de diagnostico. Evidencia sanitizada: no contiene passwords SIP ni secrets de Asterisk.",
        "",
        "RESUMEN",
        "  Avaya detectados: {}".format(s.get("total", "0")),
        "  Configurados: {}".format(s.get("configured", "0")),
        "  Registrados: {}".format(s.get("registered", "0")),
        "  Configurados sin registro: {}".format(s.get("not_registered", "0")),
        "  Solo detectados: {}".format(s.get("detected_only", "0")),
        "  Presencia IP + MAC confirmada: {}".format(s.get("live_confirmed", "0")),
        "  IP viva / MAC no verificable: {}".format(s.get("live_ip_only", "0")),
        "  MAC viva distinta: {}".format(s.get("live_mac_mismatch", "0")),
        "  Sin respuesta ICMP / filtrado: {}".format(s.get("live_unreachable", "0")),
        "  Credenciales MATCH: {}".format(s.get("credentials_match", "0")),
        "  Credenciales MISMATCH: {}".format(s.get("credentials_mismatch", "0")),
        "  Credenciales UNKNOWN: {}".format(s.get("credentials_unknown", "0")),
        "  Archivo solicitado: {}".format(s.get("config_requested", "0")),
        "  Sin evidencia de descarga: {}".format(s.get("config_not_requested", "0")),
        "",
        "TELEFONOS CONFIGURADOS",
    ]

    configured = [e for e in report.get("endpoints", []) if e.get("account", "NONE") != "NONE"]
    detected = [e for e in report.get("endpoints", []) if e.get("account", "NONE") == "NONE"]

    for ep in configured:
        cred = "{}/{}".format(ep.get("credential_user", "UNKNOWN"), ep.get("credential_secret", "UNKNOWN"))
        lines.extend([
            "",
            "Ext. {} | {} | {}".format(safe(ep.get("account")), safe(ep.get("model")), safe(ep.get("state"))),
            "  MAC DB: {} | ultima IP: {} | live: {}".format(safe(ep.get("mac")), safe(ep.get("last_ip")), safe(ep.get("live_state"))),
            "  live MAC: {} | match: {} | neighbor: {} | ping: {}".format(safe(ep.get("live_mac")), safe(ep.get("live_mac_match")), safe(ep.get("neighbor_state")), safe(ep.get("ping"))),
            "  provisioning: {} | credenciales user/secret: {} | descarga: {} HTTP {}".format(safe(ep.get("provisioning")), cred, safe(ep.get("config_request")), safe(ep.get("request_http"))),
            "  request IP: {} | request time: {}".format(safe(ep.get("request_ip")), safe(ep.get("request_time"))),
            "  SIP IP: {} | SIP status: {}".format(safe(ep.get("sip_ip")), safe(ep.get("sip_status"))),
            "  User-Agent: {}".format(safe(ep.get("useragent"))),
            "  last scanned: {} | last modified: {}".format(safe(ep.get("last_scanned")), safe(ep.get("last_modified"))),
        ])

    lines.extend(["", "DETECTADOS SIN EXTENSION"])
    for ep in detected:
        lines.append(
            "  {} | {} | IP {} | live {} | live MAC {} | match {} | scan {}".format(
                safe(ep.get("model")), safe(ep.get("mac")), safe(ep.get("last_ip")),
                safe(ep.get("live_state")), safe(ep.get("live_mac")), safe(ep.get("live_mac_match")),
                safe(ep.get("last_scanned")),
            )
        )

    lines.extend(["", "FABRICANTES"])
    for mf in report.get("manufacturers", []):
        lines.append("  {}: {} endpoint(s)".format(safe(mf.get("name")), safe(mf.get("endpoints"))))

    lines.extend([
        "",
        "NOTAS",
        "  LIVE_CONFIRMED requiere respuesta IP y coincidencia de MAC observada con Endpoint Configurator.",
        "  UNREACHABLE_OR_FILTERED no demuestra que el telefono este apagado; ICMP puede estar filtrado.",
        "  En redes enrutadas la MAC de neighbor puede corresponder al siguiente salto y debe interpretarse con cautela.",
    ])
    return lines


def pdf_escape(text):
    return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def write_pdf(report, path):
    # Minimal dependency-free PDF using the built-in Helvetica font.
    wrapped = []
    for line in report_lines(report):
        if not line:
            wrapped.append("")
            continue
        wrapped.extend(textwrap.wrap(line, width=105, subsequent_indent="    ") or [""])

    page_lines = 52
    pages = [wrapped[i:i + page_lines] for i in range(0, len(wrapped), page_lines)] or [["No data"]]

    objects = []
    objects.append("<< /Type /Catalog /Pages 2 0 R >>")
    kids = " ".join("{} 0 R".format(4 + i * 2) for i in range(len(pages)))
    objects.append("<< /Type /Pages /Kids [{}] /Count {} >>".format(kids, len(pages)))
    objects.append("<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")

    for idx, lines in enumerate(pages):
        page_obj = 4 + idx * 2
        content_obj = page_obj + 1
        stream = ["BT", "/F1 9 Tf", "45 800 Td", "11 TL"]
        for line in lines:
            stream.append("({}) Tj".format(pdf_escape(line.encode("latin-1", "replace").decode("latin-1"))))
            stream.append("T*")
        stream.append("ET")
        stream_text = "\n".join(stream) + "\n"
        objects.append("<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 842] /Resources << /Font << /F1 3 0 R >> >> /Contents {} 0 R >>".format(content_obj))
        objects.append("<< /Length {} >>\nstream\n{}endstream".format(len(stream_text.encode("latin-1")), stream_text))

    header = b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n"
    body = bytearray(header)
    offsets = [0]
    for num, obj in enumerate(objects, 1):
        offsets.append(len(body))
        body.extend("{} 0 obj\n{}\nendobj\n".format(num, obj).encode("latin-1", "replace"))

    xref = len(body)
    body.extend("xref\n0 {}\n".format(len(objects) + 1).encode("ascii"))
    body.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        body.extend("{:010d} 00000 n \n".format(offset).encode("ascii"))
    body.extend("trailer\n<< /Size {} /Root 1 0 R >>\nstartxref\n{}\n%%EOF\n".format(len(objects) + 1, xref).encode("ascii"))

    with open(path, "wb") as fh:
        fh.write(body)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("log")
    parser.add_argument("--json", dest="json_path", required=True)
    parser.add_argument("--pdf", dest="pdf_path", required=True)
    args = parser.parse_args()

    report = parse_log(args.log)
    write_json(report, args.json_path)
    write_pdf(report, args.pdf_path)

    if not os.path.getsize(args.json_path) or not os.path.getsize(args.pdf_path):
        raise SystemExit("empty report output")
    print("CEIBA-AVAYA-FLEET-EXPORT-PASS json={} pdf={}".format(args.json_path, args.pdf_path))


if __name__ == "__main__":
    main()
