import json

import click
import requests

from mongogrant.client import Client

remotes = Client().remotes()
DEFAULT_ENDPOINT = remotes[0]["endpoint"] if remotes else None


@click.group()
def cli():
    """Run `mgrant init --help` to get started."""
    pass


@click.command()
@click.option('--endpoint', default=DEFAULT_ENDPOINT,
              help='auth server. default: "{}"'.format(DEFAULT_ENDPOINT))
@click.argument('email')
def init(endpoint, email):
    """Request a token.

    EMAIL: Your email address registered with your mongogrant administrator.
    """
    if endpoint is None:
        print("You have no saved endpoints. Provide an endpoint argument.")
        return

    rv = requests.get("{}/gettoken/{}".format(endpoint, email))
    print(rv.json())
    print("Copy the fetch token from the link and run `mgrant settoken`.")


@click.command()
@click.option('--endpoint', default=DEFAULT_ENDPOINT,
              help='auth server. default: "{}"'.format(DEFAULT_ENDPOINT))
@click.argument('token')
def settoken(endpoint, token):
    """Set token for a remote"""
    if endpoint is None:
        print("You have no saved endpoints. Provide an endpoint argument.")
        return

    client = Client()
    client.set_remote(endpoint, token)
    print("Remember that tokens expire. Run `mgrant init` to request "
          "a fresh token for an endpoint.")
    print("Run `mgrant db` to get credentials for a database.")


@click.command()
@click.argument('host')
@click.argument('db')
@click.option('--role', default='read', help='"read" or "readWrite"')
@click.option('--atomate-starters', is_flag=True, default=False,
              help='Print db.json and my_launchpad.yaml files')
def db(db, role, host, atomate_starters):
    """
    Get credentials for a database.

    Args:
        host: Database host. Ask your mongogrant administrator
        db: Database name. Ask your mongogrant administrator
    """
    if atomate_starters and role == 'read':
        print("Need '--role readWrite' for atomate credentials.")
        return
    client = Client()
    if atomate_starters:
        db_rw = client.db("{}:{}/{}".format(role, host, db))
        admin = client.get_auth(host, db, role)
        db_ro = client.db("{}:{}/{}".format("read", host, db))
        readonly = client.get_auth(host, db, "read")
        db_json = dict(
            host=host,
            database=db,
            collection="tasks",
            admin_user=admin['username'],
            admin_password=admin['password'],
            readonly_user=readonly['username'],
            readonly_password=readonly['password'],
            aliases={}
        )
        print(json.dumps(db_json, indent=2))
        my_launchpad = my_launchpad_template.format(
            host, db, admin['username'], admin['password'])
        print(my_launchpad)
    else:
        db_we = client.db("{}:{}/{}".format(role, host, db))
        print("Wrote credentials to ~/.mongogrant.json")


my_launchpad_template = """
host: {}
name: {}
username: {}
password: {}
ssl_ca_file: null
logdir: null
strm_lvl: INFO
user_indices: []
wf_user_indices: []
"""

@click.command()
@click.option('--endpoint', default=DEFAULT_ENDPOINT,
              help='auth server. default: "{}"'.format(DEFAULT_ENDPOINT))
@click.argument('email')
@click.argument('spec')
def allow(endpoint, email, spec):
    """
    [Admins only] Set allow rules for users.

    Args:
        endpoint (str): Mongogrant endpoint. Defaults to that of your first
            remote.
        email (str): Email address of user to update.
        spec (str): mongogrant spec, e.g. "ro:host/dbname", "rw:host/dbname"

    """
    client = Client()
    remote = next(r for r in client.remotes() if r["endpoint"] == endpoint)
    token = remote["token"]
    role, host_db = spec.split(":")
    host, db = host_db.split("/")
    if role not in ("ro", "read", "rw", "readWrite"):
        print("Role not recognized")
        return

    if role == "ro":
        role = "read"
    elif role == "rw":
        role = "readWrite"
    rv = requests.post("{}/setrule/{}".format(endpoint, token), data=dict(
        email=email, host=host, db=db, role=role, which="allow",
    ))
    if rv.json()["success"] == "true":
        print("{} is now authorized to obtain {} credentials for {}/{} "
              "via mongogrant (from remote \"{}\").".format(
            email, "read" if role == "read" else "read and readWrite",
            host, db, endpoint,
        ))
    else:
        print("Rule setting failed: {}", format(rv.text))


cli.add_command(init)
cli.add_command(settoken)
cli.add_command(db)
cli.add_command(allow)