#!/usr/bin/env python3
"""Generate sanitized Test 53 reports in Markdown, JSON and PDF.

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
    endpoints, manufacturers, summary = [], [], {}
    schema = scope = None
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


def safe(value, default="NONE"):
    return str(value or default).replace("\\ ", " ").replace("|", "\\|").replace("\n", " ")


def n(summary, key):
    try:
        return int(summary.get(key, "0"))
    except ValueError:
        return 0


def cred_status(ep):
    user = ep.get("credential_user", "UNKNOWN")
    secret = ep.get("credential_secret", "UNKNOWN")
    if user == "MATCH" and secret == "MATCH": return "✅ MATCH"
    if user == "MISMATCH" or secret == "MISMATCH": return "❌ MISMATCH"
    return "⚠️ UNKNOWN"


def download_status(ep):
    if ep.get("config_request") == "YES":
        code = ep.get("request_http", "UNKNOWN")
        return "{} YES ({})".format("✅" if code.startswith("2") else "⚠️", code)
    return "⚠️ NO EVIDENCE"


def sip_status(ep): return "✅ REGISTERED" if ep.get("state") == "CONFIGURED_REGISTERED" else "❌ NOT REGISTERED"


def live_status(ep):
    return {"LIVE_CONFIRMED": "✅ LIVE + MAC MATCH", "LIVE_IP_MAC_MISMATCH": "🚨 MAC MISMATCH", "LIVE_IP_ONLY": "⚠️ LIVE IP / MAC UNKNOWN", "UNREACHABLE_OR_FILTERED": "⚠️ NO ICMP"}.get(ep.get("live_state", "UNKNOWN"), "❓ UNKNOWN")


def write_json(report, path):
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(report, fh, ensure_ascii=False, indent=2, sort_keys=True); fh.write("\n")


def markdown_lines(report):
    s = report.get("summary", {}); endpoints = report.get("endpoints", [])
    configured = [e for e in endpoints if e.get("account", "NONE") != "NONE"]
    detected = [e for e in endpoints if e.get("account", "NONE") == "NONE"]
    issues = [e for e in configured if e.get("state") != "CONFIGURED_REGISTERED" or e.get("live_mac_match") == "MISMATCH"]
    lines = ["# 📞 Ceiba - Avaya Fleet Audit", "", "> Auditoría de diagnóstico **sin cambios de configuración**. La prueba envía un ping corto para refrescar presencia/neighbor y nunca muestra contraseñas SIP.", "", "## Estado general", "", "| Indicador | Resultado |", "|---|---:|",
             "| 🔎 Avaya detectados | **{}** |".format(n(s, "total")), "| ⚙️ Configurados | **{}** |".format(n(s, "configured")), "| ✅ Registrados | **{}** |".format(n(s, "registered")), "| ❌ Configurados sin registro | **{}** |".format(n(s, "not_registered")), "| 💤 Solo detectados | **{}** |".format(n(s, "detected_only")), "| 🟢 Presencia IP + MAC confirmada | **{}** |".format(n(s, "live_confirmed")), "| 🟡 IP responde pero MAC no verificable | **{}** |".format(n(s, "live_ip_only")), "| 🚨 MAC viva distinta a Endpoint Configurator | **{}** |".format(n(s, "live_mac_mismatch")), "| ⚠️ Sin respuesta ICMP / filtrado | **{}** |".format(n(s, "live_unreachable")), "| 🔐 Credenciales coinciden | **{}** |".format(n(s, "credentials_match")), "| 🚨 Credenciales distintas | **{}** |".format(n(s, "credentials_mismatch")), "| ❓ Credenciales no verificables | **{}** |".format(n(s, "credentials_unknown")), "| 📥 Archivo solicitado | **{}** |".format(n(s, "config_requested")), "| ⚠️ Sin evidencia de descarga | **{}** |".format(n(s, "config_not_requested")), ""]
    if issues:
        lines += ["## 🚨 Requieren atención", ""]
        for ep in issues: lines.append("- **Ext. {}** · {} · {} · MAC `{}` · última IP `{}`".format(safe(ep.get("account")), safe(ep.get("state")), live_status(ep), safe(ep.get("mac")), safe(ep.get("last_ip"))))
        lines.append("")
    else: lines += ["## ✅ Sin incidencias en los Avaya configurados", ""]
    lines += ["## Teléfonos Avaya configurados", "", "| Ext. | Modelo | MAC DB | Última IP | Presencia actual | Provisioning | Credenciales | Descarga config | SIP |", "|---:|---|---|---|---|---|---|---|---|"]
    for ep in configured:
        prov = "✅ PRESENT" if ep.get("provisioning") == "PRESENT" else "❌ MISSING"
        lines.append("| {} | {} | `{}` | `{}` | {} | {} | {} | {} | {} |".format(safe(ep.get("account")), safe(ep.get("model")), safe(ep.get("mac")), safe(ep.get("last_ip")), live_status(ep), prov, cred_status(ep), download_status(ep), sip_status(ep)))
    lines += ["", "## Avaya detectados sin extensión", "", "| Modelo | MAC DB | Última IP | Último scan | Presencia actual | MAC viva | Coincidencia |", "|---|---|---|---|---|---|---|"]
    for ep in detected: lines.append("| {} | `{}` | `{}` | `{}` | {} | `{}` | **{}** |".format(safe(ep.get("model")), safe(ep.get("mac")), safe(ep.get("last_ip")), safe(ep.get("last_scanned")), live_status(ep), safe(ep.get("live_mac")), safe(ep.get("live_mac_match"))))
    lines += ["", "## Fabricantes vistos por Endpoint Configurator", ""]
    for mf in report.get("manufacturers", []): lines.append("- **{}**: {} endpoint(s)".format(safe(mf.get("name")), safe(mf.get("endpoints"))))
    lines += ["", "---", "Archivos descargables: TXT (evidencia sanitizada), JSON (datos estructurados) y PDF (reporte legible)."]
    return lines


def write_markdown(report, path):
    with open(path, "a", encoding="utf-8") as fh: fh.write("\n".join(markdown_lines(report)) + "\n")


def report_lines(report):
    s = report.get("summary", {}); lines = ["CEIBA - AVAYA FLEET AUDIT", "", "Auditoria sanitizada: no contiene passwords SIP ni secrets de Asterisk.", "", "RESUMEN", "  Avaya detectados: {}".format(s.get("total", "0")), "  Configurados: {}".format(s.get("configured", "0")), "  Registrados: {}".format(s.get("registered", "0")), "  Sin registro: {}".format(s.get("not_registered", "0")), "  Solo detectados: {}".format(s.get("detected_only", "0")), "  Live confirmados: {}".format(s.get("live_confirmed", "0")), "  MAC mismatch: {}".format(s.get("live_mac_mismatch", "0")), "", "TELEFONOS CONFIGURADOS"]
    for ep in report.get("endpoints", []):
        if ep.get("account", "NONE") != "NONE":
            lines += ["", "Ext. {} | {} | {}".format(safe(ep.get("account")), safe(ep.get("model")), safe(ep.get("state"))), "  MAC DB: {} | IP: {} | live: {} | live MAC: {} | match: {}".format(safe(ep.get("mac")), safe(ep.get("last_ip")), safe(ep.get("live_state")), safe(ep.get("live_mac")), safe(ep.get("live_mac_match"))), "  provisioning: {} | creds: {}/{} | descarga: {} HTTP {}".format(safe(ep.get("provisioning")), safe(ep.get("credential_user")), safe(ep.get("credential_secret")), safe(ep.get("config_request")), safe(ep.get("request_http"))), "  SIP IP: {} | SIP status: {} | UA: {}".format(safe(ep.get("sip_ip")), safe(ep.get("sip_status")), safe(ep.get("useragent")))]
    lines += ["", "DETECTADOS SIN EXTENSION"]
    for ep in report.get("endpoints", []):
        if ep.get("account", "NONE") == "NONE": lines.append("  {} | {} | IP {} | live {} | live MAC {} | match {}".format(safe(ep.get("model")), safe(ep.get("mac")), safe(ep.get("last_ip")), safe(ep.get("live_state")), safe(ep.get("live_mac")), safe(ep.get("live_mac_match"))))
    return lines


def pdf_escape(text): return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def write_pdf(report, path):
    wrapped=[]
    for line in report_lines(report): wrapped.extend(textwrap.wrap(line, width=105, subsequent_indent="    ") or [""])
    pages=[wrapped[i:i+52] for i in range(0,len(wrapped),52)] or [["No data"]]
    objects=["<< /Type /Catalog /Pages 2 0 R >>", "<< /Type /Pages /Kids [{}] /Count {} >>".format(" ".join("{} 0 R".format(4+i*2) for i in range(len(pages))),len(pages)), "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>"]
    for idx, lines in enumerate(pages):
        page_obj=4+idx*2; content_obj=page_obj+1; stream=["BT","/F1 9 Tf","45 800 Td","11 TL"]
        for line in lines: stream += ["({}) Tj".format(pdf_escape(line.encode("latin-1","replace").decode("latin-1"))),"T*"]
        stream.append("ET"); stream_text="\n".join(stream)+"\n"
        objects += ["<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 842] /Resources << /Font << /F1 3 0 R >> >> /Contents {} 0 R >>".format(content_obj), "<< /Length {} >>\nstream\n{}endstream".format(len(stream_text.encode("latin-1")),stream_text)]
    body=bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n"); offsets=[0]
    for num,obj in enumerate(objects,1): offsets.append(len(body)); body.extend("{} 0 obj\n{}\nendobj\n".format(num,obj).encode("latin-1","replace"))
    xref=len(body); body.extend("xref\n0 {}\n".format(len(objects)+1).encode("ascii")); body.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]: body.extend("{:010d} 00000 n \n".format(offset).encode("ascii"))
    body.extend("trailer\n<< /Size {} /Root 1 0 R >>\nstartxref\n{}\n%%EOF\n".format(len(objects)+1,xref).encode("ascii"))
    with open(path,"wb") as fh: fh.write(body)


def main():
    p=argparse.ArgumentParser(); p.add_argument("log"); p.add_argument("--json",dest="json_path",required=True); p.add_argument("--pdf",dest="pdf_path",required=True); p.add_argument("--summary",dest="summary_path"); args=p.parse_args()
    report=parse_log(args.log); write_json(report,args.json_path); write_pdf(report,args.pdf_path)
    if args.summary_path: write_markdown(report,args.summary_path)
    if not os.path.getsize(args.json_path) or not os.path.getsize(args.pdf_path): raise SystemExit("empty report output")
    print("CEIBA-AVAYA-FLEET-EXPORT-PASS json={} pdf={}".format(args.json_path,args.pdf_path))


if __name__ == "__main__": main()
