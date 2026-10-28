from worlds.LauncherComponents import Component, Type, components, launch


def run_client(*args: str) -> None:
    from .client import launch as launch_client
    launch(launch_client, name="Mass Effect LE3 Client", args=args)


components.append(Component("Mass Effect LE3 Client", func=run_client, game_name="Mass Effect Legendary Edition 3",
                            component_type=Type.CLIENT, supports_uri=True))
