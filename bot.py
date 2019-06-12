import argparse
import datetime
import itertools
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
                with open(f'{prefix}/{name}.{extension}', mode='r', encoding='utf-8') as file:
                    return file.read().strip()
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
STATUS_TXT: str = load_text('status')

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
            except (UsageError, ValueError, data.nx.NetworkXAlgorithmError) as e:
                text = '\n\n'.join([USAGE_ERROR_TXT, format_exception_md(e),
                                    'See /help for usage info.'])
                markdown_safe_reply(update.message, text)
                logging.info(f'served {command_info} (usage/algorithm error)')
            except Exception as e:
                text = '\n\n'.join([INTERNAL_ERROR_TXT, format_exception_md(e)])
                markdown_safe_reply(update.message, text)
                logging.error(f'{command_info}: unexpected exception', exc_info=e)
            finally:
                logging.debug(f'exiting {command_info}')

        handler = tge.CommandHandler(command, decorated, **handler_kwargs)
        DISPATCHER.add_handler(handler)
        return decorated

    return decorator


def progress(callback: CommandCallbackType) -> CommandCallbackType:
    """
    Decorator to show a "loading" message during a command handler callback
    :param callback: command callback to decorate (context-based)
    """

    def decorated(update: tg.Update, context: tge.CallbackContext):
        prompt_gen = itertools.cycle('Processing{:<3} ⏱'.format('.' * i) for i in range(4))
        progress_message: tg.Message = update.message.reply_text(next(prompt_gen))

        def progress_job_callback(context: tge.CallbackContext):
            try:
                progress_message.edit_text(next(prompt_gen))
            except tg.error.BadRequest:
                context.job.schedule_removal()  # shutdown if already deleted

        logging.debug(f'adding progress message to {update.effective_chat.id}')
        job: tge.Job = context.job_queue.run_repeating(progress_job_callback, 0.5)
        try:
            callback(update, context)
        finally:
            logging.debug(f'removing progress message from {update.effective_chat.id}')
            job.schedule_removal()
            progress_message.delete()

    decorated.__name__ = callback.__name__  # to work with cmdhandler decorator defaults
    return decorated


# ------------------------ Command handlers ------------------------

@cmdhandler()
@progress
def start(update: tg.Update, context: tge.CallbackContext):
    chat_data = context.chat_data
    chat_data['last_fetch_time'] = datetime.datetime.now()
    chat_data['stations'] = data.fetch_stations()
    chat_data['graph'] = data.BicingGraph.from_dataframe(chat_data['stations'])
    update.message.reply_markdown(START_TXT)


@cmdhandler(command='help')
def help_cmd(update: tg.Update, _: tge.CallbackContext):
    update.message.reply_markdown(HELP_TXT, disable_web_page_preview=True)


@cmdhandler()
def authors(update: tg.Update, _: tge.CallbackContext):
    update.message.reply_markdown(AUTHORS_TXT, disable_web_page_preview=True)


@cmdhandler()
def status(update: tg.Update, context: tge.CallbackContext):
    chat_data = context.chat_data

    def lines():
        graph = chat_data.get('graph', None)
        if graph:
            yield 'Initialised: `True`'
            time = chat_data['last_fetch_time'].isoformat(sep=' ', timespec='minutes')
            yield f"Last fetch time: `{time}`"
            yield f"Current graph distance: `{graph.distance} m`"
        else:
            yield 'Initialised: `False`'

    update.message.reply_markdown('\n'.join([STATUS_TXT, *lines()]))


@cmdhandler(command='graph')
@progress
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
@progress
def plotgraph(update: tg.Update, context: tge.CallbackContext):
    graph = get_graph(context)
    image = data.save_image_to_memory(graph.plot())
    update.message.reply_photo(photo=image)


@cmdhandler()
@progress
def route(update: tg.Update, context: tge.CallbackContext):
    graph = get_graph(context)
    context.args = ' '.join(context.args).split(',')
    origin, destination, = get_args(context, types=(('origin', str), ('destination', str),))

    origin = data.address_to_coord(origin)
    destination = data.address_to_coord(destination)

    path, total_seconds = graph.route(origin, destination)
    time = datetime.timedelta(seconds=int(total_seconds))
    image = data.save_image_to_memory(path.plot())
    update.message.reply_photo(photo=image, caption=f'Expected duration of the route: {time}')


@cmdhandler()
@progress
def distribute(update: tg.Update, context: tge.CallbackContext):
    graph = get_graph(context)
    min_bikes, min_free_docks = get_args(context, (('min_bikes', int), ('min_bikes', int)))
    total_cost, flow_dict = graph.distribute(min_bikes, min_free_docks)

    def lines():
        yield f'Total cost of redistribution: `{total_cost} bikes·m`'
        if total_cost > 0:
            tail, head, flow, dist = graph.max_cost_edge(flow_dict)
            yield f'Maximal edge cost: `{tail.Index} --> {head.Index}: {flow * dist} ' \
                f'({flow} bikes · {dist} m`)'

    update.message.reply_markdown('\n'.join(lines()))


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
    # TODO: switch to ArgParse
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


def markdown_safe_reply(original_message: tg.Message, reply_txt: str):
    """
    Tries to reply to ``original_message`` in Markdown; falls back to plain text
    if it can't be parsed correctly.
    """
    try:
        original_message.reply_markdown(reply_txt)
    except tg.error.BadRequest:
        original_message.reply_text(reply_txt)


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
    command_line_args = parser.parse_args()
    start_bot(command_line_args.level)
