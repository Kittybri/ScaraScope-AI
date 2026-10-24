# ScaraScope on Oracle Cloud Infrastructure

This deployment runs the existing web app and FastAPI service on an Ubuntu
24.04 LTS Compute VM. An optional Compose profile runs the Discord client.
Oracle hosts the application; language generation still needs a configured
provider. An Oracle account alone does not provide an LLM or a Discord token.

The default is **private access through SSH**, using one API worker and a
generated shared API key. Port 8000 binds to the VM's loopback interface only.
No public web endpoint, Oracle IAM policy, billing upgrade, or third-party
account is created by these files. SQLite data persists in a Docker volume.
This is a prototype deployment, not a claim of production readiness or user
data isolation. Review [the existing security limits](../../docs/SECURITY.md).

## 1. Create the VM

In OCI Compute, choose your home region and create an instance:

- Name: `scarascope-ai`.
- Image: **Canonical Ubuntu 24.04 LTS**, matching the shape architecture.
- Shape: an **Always Free-eligible** shape within your tenancy's remaining
  allowances. A small Ampere A1 VM is preferable to a 1 GiB micro VM for builds.
  Check the current console eligibility and estimated cost before launching;
  availability and free quotas depend on the account and region.
- Boot volume: 50 GB unless you have another reviewed storage plan.
- Network: a public subnet with an internet gateway if using direct SSH.
- Upload your own public SSH key and retain the private key securely.
- Restrict SSH (TCP 22) to your trusted source CIDR. Keep TCP 8000 and Ollama
  port 11434 closed. No web ingress is needed for this private deployment.

Under advanced options, paste [cloud-init.yaml](cloud-init.yaml) as the
initialization script. Review `SCARASCOPE_REF` first: `main` must contain these
deployment files, or replace it with the reviewed branch/commit you intend
to deploy. The VM needs outbound DNS and HTTPS to Ubuntu, Docker, PyPI and
GitHub; later SEC/Groq access also uses outbound HTTPS.

After launch, connect with SSH and wait for provisioning:

```bash
ssh -i /path/to/private-key ubuntu@VM_PUBLIC_IP
sudo cloud-init status --wait
sudo tail -n 80 /var/log/cloud-init-output.log
curl --fail http://127.0.0.1:8000/api/health
```

If you did not use cloud-init, install Docker Engine and its Compose plugin
using [Docker's Ubuntu instructions](https://docs.docker.com/engine/install/ubuntu/),
clone this repository to `/opt/scarascope-ai`, check out the reviewed version,
and run `sudo bash deploy/oracle/deploy.sh` from the repository root.

## 2. Open the web app privately

On your own computer, keep this tunnel running:

```bash
ssh -i /path/to/private-key -N -L 8000:127.0.0.1:8000 ubuntu@VM_PUBLIC_IP
```

Open <http://127.0.0.1:8000>. Use a different local port if 8000 is occupied.
Retrieve `SCARASCOPE_API_KEY` from `/opt/scarascope-ai/deploy/oracle/.env` in
your private SSH session and enter it into the web app's API-key field. Do
not paste it into GitHub, chat, issue comments, screenshots, or provisioning
logs. Unauthenticated research requests must return HTTP 401.

The fictional `DEMO` works immediately. For live SEC research, edit the
VM-only environment file with `sudoedit /opt/scarascope-ai/deploy/oracle/.env`
and set `SEC_USER_AGENT` to your application name and real contact email.
For optional LLM synthesis, set `GROQ_API_KEY` there. Then rerun:

```bash
cd /opt/scarascope-ai
sudo bash deploy/oracle/deploy.sh
```

Ollama is disabled in this deployment. Do not use your laptop's localhost
address as a cloud model endpoint. Configure any future private model network
separately and respect the application's `local_only` policy.

## 3. Enable Discord later

Set `DISCORD_BOT_TOKEN` in the VM's untracked `.env`, enable Message Content
Intent in the Discord Developer Portal, and run:

```bash
cd /opt/scarascope-ai
sudo bash deploy/oracle/deploy.sh --discord
```

Discord connects outbound and talks to `http://api:8000` on the private
Compose network. It requires no public web port. Coordinate with the owner
before starting another worker for the same Discord bot token. Stop it with:

```bash
cd /opt/scarascope-ai/deploy/oracle
sudo docker compose --env-file .env --profile discord stop discord
```

## 4. Optional manual deployment from GitHub Actions

The [manual workflow](../../.github/workflows/deploy-oracle.yml) updates an
**existing** `/opt/scarascope-ai` checkout to the exact selected workflow
commit and runs the deploy script. It does not provision OCI infrastructure,
run automatically on pushes, or merge branches.

After reviewing who can deploy, configure a GitHub environment named `oracle`
with required reviewers and appropriate deployment-branch restrictions. Add:

| Environment secret | Value |
| --- | --- |
| `OCI_HOST` | VM public IPv4 address or DNS name |
| `OCI_SSH_USER` | SSH user, normally `ubuntu` |
| `OCI_SSH_PRIVATE_KEY` | A dedicated deployment key authorized on this VM |
| `OCI_SSH_KNOWN_HOSTS` | Verified OpenSSH known-hosts entry for that host |

Validate the SSH host-key fingerprint using an independently trusted console
or session. `ssh-keyscan` alone is not verification. The workflow refuses
unknown or changed host keys. The SSH user must have passwordless sudo for
deployment; **this grants the workflow administrative access to the VM**.
Do not share the operator's personal private key or add a deployment key
until this access is approved. GitHub-hosted runners also need network access
to SSH; the default administrator-only ingress rule will not admit them.
Plan an approved runner/network route before using the workflow rather than
opening SSH to everyone.

Once the workflow is on the default branch, use **Actions → Deploy to Oracle
Compute (manual) → Run workflow** and select the reviewed branch. Leave
runtime API/model/Discord secrets on the VM; they are not workflow inputs.

## Operations and recovery

```bash
cd /opt/scarascope-ai/deploy/oracle
sudo docker compose --env-file .env ps
sudo docker compose --env-file .env logs --tail 100 api
sudo docker compose --env-file .env stop
```

Docker starts the services after a VM reboot. Re-running `deploy.sh` keeps
the current `.env` and named data volume. Do not run `down --volumes` unless
you intend to delete research history/watchlists. Back up the volume and
private `.env` securely before upgrades; SQLite backups should use its backup
API or a stopped service. To roll back, check out a reviewed earlier commit
containing these deployment files and rerun the deploy script. Existing data
formats still need compatibility review; this does not guarantee migration
rollback.

A future public website needs a domain, HTTPS reverse proxy, actual request
body limits, and a reviewed ingress policy before exposing the service.

References: [OCI instance creation](https://docs.oracle.com/en-us/iaas/Content/Compute/Tasks/launchinginstance.htm),
[current Always Free allowances](https://docs.oracle.com/en-us/iaas/Content/FreeTier/freetier_topic-Always_Free_Resources.htm),
[Docker Compose profiles](https://docs.docker.com/compose/how-tos/profiles/).
