import logging
from traceback import format_exception_only

import telegram as tg
import telegram.ext as tge

from data import *


class UsageError(Exception):
    pass


# ------------------------ Bot initialization ------------------------

def load_text(name: str) -> str:
    """
    Utility to read and return the entire contents of a text file. Searches the
    `text` sub-folder first and then the root working directory.
    :param name: name of the text file
    """
    for prefix in ('text', '.'):
        for extension in ('md', 'txt', ''):
            try:
                with open(f'{prefix}/{name}.{extension}', 'r') as text_file:
                    return text_file.read().strip()
            except FileNotFoundError:
                continue
    raise FileNotFoundError(f'could not find `{name}` text file')


# Construct bot objects
TOKEN: str = load_text('token')
UPDATER = tge.Updater(token=TOKEN, use_context=True)
DISPATCHER = UPDATER.dispatcher
BOT = UPDATER.bot

# Load text files:
START_TXT: str = load_text('start')
HELP_TXT: str = load_text('help')
AUTHORS_TXT: str = load_text('authors')
ERROR_TXT: str = load_text('error')


# ------------------------ Command handlers ------------------------

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
    chat_data = context.chat_data
    chat_data['stations'] = fetch_stations()
    chat_data['graph'] = BicingGraph.from_dataframe(chat_data['stations'])


@cmdhandler()
def help(update: tg.Update, context: tge.CallbackContext):
    update.message.reply_markdown(HELP_TXT)


@cmdhandler()
def authors(update: tg.Update, context: tge.CallbackContext):
    update.message.reply_markdown(AUTHORS_TXT, disable_web_page_preview=True)


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


# ------------------------ Main entry point ------------------------

def start_bot():
    logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                        level=logging.INFO)
    UPDATER.start_polling()
    logging.info('bot online')


# Main entry point if run as script:
if __name__ == '__main__':
    start_bot()
