from traceback import format_exception_only

import telegram as tg
import telegram.ext as tge

with open('token.txt') as token_file:
    TOKEN: str = token_file.read().strip()

UPDATER = tge.Updater(token=TOKEN)
DISPATCHER = UPDATER.dispatcher
BOT = UPDATER.bot


def cmdhandler(command: str = None, **handler_kwargs) -> callable:
    """
    Decorator factory for command handlers. The returned decorator adds
    the decorated function as a command handler for the command ``command``
    to the global DISPATCHER. If ``command`` is not specified it defaults to
    the decorated function's name.

    The callback is also decorated with an exception handler before
    constructing the command handler.

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
            try:
                return callback(bot, update, *args, **kwargs)
            except Exception as e:
                text = ERROR_TXT + "\n\n`{}`".format(format_exception_only(type(e), e)[0])
                update.message.reply_markdown(text)

        handler = tge.CommandHandler(command, decorated, **handler_kwargs)
        DISPATCHER.add_handler(handler)
        return callback

    return decorator


@cmdhandler()
def start(bot: tg.Bot, update: tg.Update):
    update.message.reply_markdown(START_TXT)


@cmdhandler()
def help(bot: tg.Bot, update: tg.Update):
    update.message.reply_markdown(HELP_TXT)


@cmdhandler()
def authors(bot: tg.Bot, update: tg.Update):
    update.message.reply_markdown(AUTHORS_TXT)


@cmdhandler()
def graph(bot: tg.Bot, update: tg.Update):
    raise NotImplementedError


@cmdhandler()
def nodes(bot: tg.Bot, update: tg.Update):
    raise NotImplementedError


@cmdhandler()
def edges(bot: tg.Bot, update: tg.Update):
    raise NotImplementedError


@cmdhandler()
def components(bot: tg.Bot, update: tg.Update):
    raise NotImplementedError


@cmdhandler()
def route(bot: tg.Bot, update: tg.Update):
    raise NotImplementedError


@cmdhandler()
def plotgraph(bot: tg.Bot, update: tg.Update):
    raise NotImplementedError


def start_bot():
    import logging
    logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                        level=logging.INFO)

    UPDATER.start_polling()




START_TXT: str
HELP_TXT: str
AUTHORS_TXT: str
ERROR_TXT: str

# Load text files:
for text_name in ('start', 'help', 'authors', 'error'):
    text_var = '{}_TXT'.format(text_name.upper())
    with open('text/{}.md'.format(text_name), 'r') as text_file:
        globals()[text_var] = text_file.read().strip()


# Main entry point if run as script:
if __name__ == '__main__':
    start_bot()
