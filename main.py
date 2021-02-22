import os
import configparser
from fastapi import FastAPI, Query, Header
import dns.tsigkeyring
import dns.update
import dns.query
from pathlib import Path, PurePath
import time


config = configparser.ConfigParser()
config.read(os.path.dirname(os.path.abspath(__file__)) + "/ddns.ini")
dns_server = config["DEFAULT"]["dns_server"]
tsig_key_name = config["DEFAULT"]["tsig_key_name"]
tsig_key = config["DEFAULT"]["tsig_key"]
dns_zone = config["DEFAULT"]["dns_zone"]
shared_key = config["DEFAULT"]["shared_key"]
conf_cleanup_key = config["DEFAULT"]["cleanup_key"]

tags_metadata = [
    {
        "name": "ddns",
        "description": "Update a dynamic DNS record.",
    },
]

app = FastAPI(
    title="Dynamic DNS Update Service",
    description="A basic dynamic DNS update service",
    version="0.1.0",
    openapi_tags=tags_metadata,
)


def update_dns_rr(hostname: str, operation: str, ipaddr: str = "127.0.0.1"):
    try:
        hostname = hostname.lower()
        keyring = dns.tsigkeyring.from_text({tsig_key_name: tsig_key})
        update = dns.update.Update(dns_zone, keyring=keyring, keyalgorithm="hmac-sha1")
        if operation == "update":
            update.replace(hostname, 60, "A", ipaddr)
            Path(os.path.join("/tmp", "ddns_" + hostname)).touch()
        elif operation == "delete":
            update.delete(hostname, "A")
            Path(os.path.join("/tmp", "ddns_" + hostname)).unlink()
        else:
            return False
        dns.query.tcp(update, dns_server)
        return True
    except:
        return False


def ddns_update(hostname: str, ipaddr: str):
    if update_dns_rr(hostname, "update", ipaddr):
        return {"status": "success"}
    else:
        return {"status": "failed"}


def ddns_delete(hostname: str):
    return update_dns_rr(hostname, "delete")


@app.get("/ddns", tags=["ddns"])
async def get_ddns(
    client_shared_key: str = Query(
        ...,
        min_length=8,
        max_length=32,
        regex="^[a-zA-Z0-9\-]+$",
    ),
    client_hostname: str = Query(
        ..., min_length=8, max_length=16, regex="^[a-zA-Z0-9\-]+$"
    ),
    x_forwarded_for: str = Header(...),
):

    if client_shared_key == shared_key:
        return ddns_update(client_hostname, x_forwarded_for)
    else:
        return {"status": "key error"}


@app.get("/cleanup")
async def get_cleanup(
    cleanup_key: str = Query(..., min_length=8, max_length=32, regex="^[a-zA-Z0-9\-]+$")
):
    if cleanup_key == conf_cleanup_key:
        p = Path("/tmp").glob("ddns_*")
        for child in p:
            if child.stat().st_mtime <= (time.time() - 21600):
                hostname = str(PurePath(child).stem).lstrip("ddns_")
                ddns_delete(hostname)

        return {"status": "done"}
    else:
        return {"status": "key error"}
