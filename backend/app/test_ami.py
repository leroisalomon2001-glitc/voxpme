# backend/app/test_ami.py (fichier temporaire, pas encore intégré aux routers)
import asyncio
import os
from panoramisk import Manager


async def main():
    manager = Manager(
        host="host.docker.internal",
        port=5038,
        username="voxpme-backend",
        secret=os.environ["AMI_PASSWORD"],
    )
    await manager.connect()
    resp = await manager.send_action({"Action": "Command", "Command": "core show version"})
    print(resp)
    manager.close()


asyncio.run(main())