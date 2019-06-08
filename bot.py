import logging
from traceback import format_exception_only

import telegram as tg
import telegram.ext as tge

with open('token.txt') as token_file:
    TOKEN: str = token_file.read().strip()

UPDATER = tge.Updater(token=TOKEN, use_context=True)
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
                           creation of the command handler (these will be passed
                           to ``telegram.ext.dispatcher.add_handler``)
    :return: the decorated function, unchanged
    """

    # Actual decorator
    def decorator(callback: callable) -> callable:
        nonlocal command
        command = command or callback.__name__

        def decorated(update: tg.Update, context: tge.CallbackContext, *args, **kwargs):
            try:
                callback(update, context, *args, **kwargs)
                logging.info(f'served /{command} @ {update.effective_chat.id}')
            except Exception as e:
                text = ERROR_TXT + "\n\n`{}`".format(format_exception_only(type(e), e)[0])
                update.message.reply_markdown(text)
                logging.info(f'/{command} @ {update.effective_chat.id} raised exception')

        handler = tge.CommandHandler(command, decorated, **handler_kwargs)
        DISPATCHER.add_handler(handler)
        return decorated

    return decorator


@cmdhandler()
def start(update: tg.Update, context: tge.CallbackContext):
    update.message.reply_markdown(START_TXT)


@cmdhandler()
def help(update: tg.Update, context: tge.CallbackContext):
    update.message.reply_markdown(HELP_TXT)


@cmdhandler()
def authors(update: tg.Update, context: tge.CallbackContext):
    update.message.reply_markdown(AUTHORS_TXT)


@cmdhandler()
def graph(update: tg.Update, context: tge.CallbackContext):
    raise NotImplementedError


@cmdhandler()
def nodes(update: tg.Update, context: tge.CallbackContext):
    raise NotImplementedError


@cmdhandler()
def edges(update: tg.Update, context: tge.CallbackContext):
    raise NotImplementedError


@cmdhandler()
def components(update: tg.Update, context: tge.CallbackContext):
    raise NotImplementedError


@cmdhandler()
def route(update: tg.Update, context: tge.CallbackContext):
    raise NotImplementedError


@cmdhandler()
def plotgraph(update: tg.Update, context: tge.CallbackContext):
    raise NotImplementedError


def start_bot():
    logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                        level=logging.INFO)
    UPDATER.start_polling()
    logging.info('bot online')


def load_text(name) -> str:
    with open(f'text/{name}.md', 'r') as text_file:
        return text_file.read().strip()


# Load text files:
START_TXT: str = load_text('start')
HELP_TXT: str = load_text('help')
AUTHORS_TXT: str = load_text('authors')
ERROR_TXT: str = load_text('error')


# Main entry point if run as script:
if __name__ == '__main__':
    start_bot()
