import logging
import os

logger = logging.getLogger(__name__)


role_name = os.getenv("GM_ROLE_NAME", "gm")
actor_id = role_name


async def create_gm_actor():
    from . import actors, player_setup, server

    await actors.create_gm_actor(
        server.get_guild(),  # always use the first guild for gm
        role_name=role_name,
        actor_id=actor_id,
    )
    response = await player_setup.setup_handles_no_welcome_new_player(
        role_name, actor_id
    )
    if response:
        logger.info(response)


async def init(clear_all: bool = False):
    from . import actors

    exists = actors.actor_exists(actor_id)
    if exists and clear_all:
        await actors.clear_actor(actor_id)
    if not exists or clear_all:
        await create_gm_actor()


def get_gm_active_handle():
    from . import handles

    handle = handles.get_active_handle(actor_id)
    return handle.handle_id
