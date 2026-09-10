# G10-19B — Official Grandstream P-value map

Status: COMPLETE

Scope: documentation/research only. No DB writes, no PBX live-code writes, no phone writes.

## Target

- Model: Grandstream GXP1625
- Firmware under test: 1.0.7.70
- Family for reuse: GXP16xx (GXP1610/1615/1620/1625/1628/1630)
- Endpoint Configurator target account: 202

## Official provisioning model

Grandstream documents automatic provisioning through configuration files obtained from a provisioning server by FTP/FTPS/TFTP/HTTP/HTTPS. The current provisioning guide includes the GXP1625 and GXP1630 in the supported GXP16xx family.

Provisioning file lookup is MAC-based (`cfg<mac>.xml` in current documentation), with model-specific and generic fallbacks supported by the family. Older/legacy binary `cfg<mac>` files remain relevant to Issabel's implementation.

## Provisioning P-values relevant to this project

| P-value | Meaning | Role in G10-19 | Issabel G10-19A |
|---|---|---|---|
| P212 | Config Upgrade Via | Selects provisioning transport | Present, set to `0` (TFTP) |
| P237 | Config Server Path | Points phone to provisioning server | Present, populated from Issabel server IP |
| P234 | Config File Prefix | Optional filename control / reprovision trigger | Not required for first proof |
| P235 | Config File Postfix | Optional filename control / reprovision trigger | Not required for first proof |
| P240 | Authenticate Config File | Optional config authentication | Not required for initial LAN proof |
| P1359 | XML Config File Password | Optional XML configuration protection | Not required for initial LAN proof |
| P1360 | Config HTTP/HTTPS Username | Used only if HTTP(S) provisioning auth is enabled | Not needed for TFTP proof |
| P1361 | Config HTTP/HTTPS Password | Used only if HTTP(S) provisioning auth is enabled | Not needed for TFTP proof |
| P6767 | Firmware Upgrade Via | Firmware transport, separate from config transport | Present in Issabel, set to `0` |
| P192 | Firmware Server Path | Firmware server, not required to configure SIP account | Do not change for first proof |

Grandstream documentation states that changes to provisioning-related values such as P212 and P237 can trigger auto-provisioning from Web UI/LCD. These are therefore the correct conceptual parameters for Issabel's legacy `_enableStaticProvisioning()` routine.

## Firmware-family notes

GXP16xx release notes document support for provisioning-server URL variables such as `$PN` and `$MAC`, including use in DHCP Option 66. GXP1625 is explicitly shown as an example model.

The manufacturer documentation also confirms automatic provisioning inside a LAN using DHCP Option 66, and for GXP16xx also Option 43. This is an official zero-touch bootstrap mechanism, not a workaround specific to Issabel.

## Cross-check against live Issabel from G10-19A

Observed in `/usr/share/issabel/endpoint-classes/class/issabel/vendor/Grandstream.py`:

- `updateLocalConfig()` creates `cfg` + lowercase compact MAC under the TFTP directory.
- `_enableStaticProvisioning()` is called after configuration generation.
- GXP140x-style devices are sent to `/cgi-bin/api.values.post` by the legacy activation path.
- `P237 = stdvars['server_ip']`.
- `P212 = '0'` for TFTP.
- `P6767 = '0'` for TFTP firmware upgrade.

Observed generated file state:

- binary `cfgc074ade86609`: present
- XML `cfgc074ade86609.xml`: absent
- UDP/69 listener at audit time: not detected
- `xinetd`: active

## Decision for G10-19C

Do not replace the existing Issabel binary generator yet. First prove whether the already-generated binary `cfg<mac>` can be served and consumed successfully. This minimizes changes and preserves compatibility with the existing Endpoint Configurator templates.

If binary delivery fails for a format/firmware reason after TFTP is proven healthy, then add an XML-generation path as a controlled fallback.

## Stop condition

G10-19B is complete when the official provisioning parameters are mapped to the live Issabel implementation and the next test path is unambiguous.

Result: COMPLETE.

Next: G10-19C — validate the current binary cfg delivery path and service prerequisites without exposing cfg payload or SIP secrets.

## Official references

- Grandstream SIP Device Provisioning Guide: https://documentation.grandstream.com/knowledge-base/sip-device-provisioning-guide/
- Grandstream GXP16xx FAQ: https://documentation.grandstream.com/knowledge-base/gxp16xx-faq/
- Grandstream GXP16xx release notes (provisioning URL variables / `$PN` / `$MAC`): https://firmware.grandstream.com/Release_Note_GXP16xx_1.0.7.18.pdf
