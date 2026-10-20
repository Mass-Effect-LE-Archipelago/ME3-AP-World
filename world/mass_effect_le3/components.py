from worlds.LauncherComponents import Component, Type, components, launch


def run_client(*args: str) -> None:
    from .client import launch as launch_client
    launch(launch_client, name="ME3 Client (Experimental)", args=args)


components.append(Component("ME3 Client (Experimental)", func=run_client, game_name="Mass Effect Legendary Edition 3",
                            component_type=Type.CLIENT, supports_uri=True))
