import telegram.ext as tge


UPDATER = tge.Updater(token="")  # TODO: insert token
DISPATCHER = UPDATER.dispatcher
BOT = UPDATER.bot


def cmdhandler(command: str = None, **handler_kwargs) -> callable:
    """
    Decorator factory for command handlers. The returned decorator adds
    the decorated function as a command handler for the command ``command``
    to the global DISPATCHER. If ``command`` is not specified it defaults to
    the decorated function's name.

    :param command: name of bot command to add a handler for
    :param handler_kwargs: additional keyword arguments for the
                           creation of the command handler
    :return: the decorated function, unchanged
    """

    # Actual decorator
    def decorator(callback: callable) -> tge.CommandHandler:
        nonlocal command
        command = command or callback.__name__

        def decorated(bot, update, *args, **kwargs):
            return callback(bot, update, *args, **kwargs)

        handler = tge.CommandHandler(command, decorated, **handler_kwargs)
        DISPATCHER.add_handler(handler)
        return callback

    return decorator


@cmdhandler()
def start(bot, update):
    raise NotImplementedError


@cmdhandler()
def help(bot, update):
    raise NotImplementedError


@cmdhandler()
def authors(bot, update):
    raise NotImplementedError


@cmdhandler()
def graph(bot, update):
    raise NotImplementedError


@cmdhandler()
def nodes(bot, update):
    raise NotImplementedError


@cmdhandler()
def edges(bot, update):
    raise NotImplementedError


@cmdhandler()
def components(bot, update):
    raise NotImplementedError


@cmdhandler()
def route(bot, update):
    raise NotImplementedError


@cmdhandler()
def plotgraph(bot, update):
    raise NotImplementedError
