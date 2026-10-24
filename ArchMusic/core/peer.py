_primed_peers = {}


async def prime_chat_peer(client, chat_id):
    """Load a chat's access hash before addressing it by numeric ID."""
    cache_key = (id(client), int(chat_id))
    if cache_key in _primed_peers:
        return _primed_peers[cache_key]

    async for dialog in client.get_dialogs():
        if dialog.chat.id == chat_id:
            peer = await client.resolve_peer(chat_id)
            _primed_peers[cache_key] = peer
            return peer

    raise RuntimeError(
        f"Configured group {chat_id} is not present in this account's dialogs"
    )
