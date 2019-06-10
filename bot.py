import argparse
import io
import logging
from typing import Callable, Tuple

import telegram as tg
import telegram.ext as tge

import data


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
OK_TXT: str = load_text('ok')
USAGE_ERROR_TXT: str = load_text('usage-error')
INTERNAL_ERROR_TXT: str = load_text('internal-error')

# ------------------------ Decorators ------------------------

# type alias for command handler callbacks
CommandCallbackType = Callable[[tg.Update, tge.CallbackContext], None]


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
    def decorator(callback: CommandCallbackType) -> CommandCallbackType:
        nonlocal command
        command = command or callback.__name__

        def decorated(update: tg.Update, context: tge.CallbackContext):
            command_info = f'/{command}@{update.effective_chat.id}'
            logging.info(f'reached {command_info}')
            try:
                callback(update, context)
                logging.info(f'served {command_info}')
            except (UsageError, ValueError) as e:
                text = '\n\n'.join([USAGE_ERROR_TXT, format_exception_md(e),
                                    'See /help for usage info.'])
                update.message.reply_markdown(text)
                logging.info(f'served {command_info} (usage error)')
            except Exception as e:
                text = '\n\n'.join([INTERNAL_ERROR_TXT, format_exception_md(e)])
                update.message.reply_markdown(text)
                logging.error(f'{command_info}: unexpected exception', exc_info=e)
            finally:
                logging.debug(f'exiting {command_info}')

        handler = tge.CommandHandler(command, decorated, **handler_kwargs)
        DISPATCHER.add_handler(handler)
        return decorated

    return decorator


@cmdhandler()
def start(update: tg.Update, context: tge.CallbackContext):
    update.message.reply_markdown(START_TXT)
    chat_data = context.chat_data
    chat_data['stations'] = data.fetch_stations()
    chat_data['graph'] = data.BicingGraph.from_dataframe(chat_data['stations'])


@cmdhandler()
def help(update: tg.Update, context: tge.CallbackContext):
    update.message.reply_markdown(HELP_TXT)


@cmdhandler()
def authors(update: tg.Update, context: tge.CallbackContext):
    update.message.reply_markdown(AUTHORS_TXT, disable_web_page_preview=True)


@cmdhandler(command='graph')
def make_graph(update: tg.Update, context: tge.CallbackContext):
    graph = get_graph(context)
    distance, = get_args(context, types=(('distance', float),))
    graph.construct_graph(distance)
    update.message.reply_markdown(OK_TXT)


@cmdhandler()
def nodes(update: tg.Update, context: tge.CallbackContext):
    graph = get_graph(context)
    update.message.reply_text(graph.number_of_nodes())


@cmdhandler()
def edges(update: tg.Update, context: tge.CallbackContext):
    graph = get_graph(context)
    update.message.reply_text(graph.number_of_edges())


@cmdhandler()
def components(update: tg.Update, context: tge.CallbackContext):
    graph = get_graph(context)
    update.message.reply_text(graph.components)


@cmdhandler()
def route(update: tg.Update, context: tge.CallbackContext):
    raise NotImplementedError


@cmdhandler()
def plotgraph(update: tg.Update, context: tge.CallbackContext):
    graph = get_graph(context)
    image = graph.plot()
    image_bytes = io.BytesIO()
    image.save(image_bytes, 'JPEG')
    image_bytes.seek(0)
    update.message.reply_photo(photo=image_bytes)


@cmdhandler()
def reset(update: tg.Update, context: tge.CallbackContext):
    context.chat_data.clear()
    update.message.reply_markdown(OK_TXT)


# ------------------------ Other utilities ------------------------

class UsageError(Exception):
    pass


class ArgValueError(UsageError, ValueError):
    pass


class ArgCountError(UsageError):
    pass


def format_exception_md(exception) -> str:
    """Format a markdown string from an exception, to be sent through Telegram"""
    assert isinstance(exception, Exception)
    msg = f'`{type(exception).__name__}`'
    extra = str(exception)
    if extra:
        msg += f'`:` {extra}'
    return msg


def get_graph(context: tge.CallbackContext) -> data.BicingGraph:
    """Checks if the current chat session has a stored graph and returns it"""
    try:
        return context.chat_data['graph']
    except KeyError:
        raise UsageError(f'graph not initialized yet (do so with /start)')


def get_args(context: tge.CallbackContext, types: Tuple[Tuple[str, callable], ...]) -> Tuple:
    """Checks and converts Telegram command arguments"""
    raw_args = context.args
    if len(raw_args) != len(types):
        raise ArgCountError(f'invalid number of arguments ({len(raw_args)}, expected {len(types)})')
    args = []
    try:
        for arg, (name, typ) in zip(raw_args, types):
            args.append(typ(arg))
    except ValueError:
        # noinspection PyUnboundLocalVariable
        raise ArgValueError(f"invalid literal for `{name}` argument: "
                            f"expected `{typ.__name__}`, got `'{arg}'`")
    return tuple(args)


# ------------------------ Main entry point ------------------------

def start_bot(logging_level: str):
    logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                        level=logging_level)
    UPDATER.start_polling()
    logging.info('bot online')


# Main entry point if run as script:
if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Start the BCNBicingBot.")
    parser.add_argument('--logging-level', '-l', action='store', default='INFO', dest='level',
                        type=lambda s: s.upper(), choices=['INFO', 'DEBUG'], help='logging level')
    args = parser.parse_args()
    start_bot(args.level)
