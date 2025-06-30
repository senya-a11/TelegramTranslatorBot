from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command, CommandStart
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from googletrans import Translator
from langdetect import detect
import sqlite3
import asyncio
import logging


# Initialize bot and dispatcher
bot = Bot(token="7939086936:AAFaQ_5Twjq0TkqRf0vWVdZVjCyODEmbBWw")
dp = Dispatcher()
translator = Translator()


# Database setup
conn = sqlite3.connect('translations.db', check_same_thread=False)
cursor = conn.cursor()
cursor.execute('''
CREATE TABLE IF NOT EXISTS vocabulary (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    word TEXT NOT NULL UNIQUE,
    translation TEXT NOT NULL
)
''')
conn.commit()


# States
class UserState(StatesGroup):
    not_translating = State()
    translating = State()
    adding_word = State()
    adding_translation = State()


# User states storage
user_data = {}


# Start command handler
@dp.message(CommandStart())
async def welcome(message: Message):
    user_data[message.chat.id] = {'state': 'not_translating', 'language': None}

    builder = InlineKeyboardBuilder()
    builder.add(
        types.InlineKeyboardButton(
            text="Start translating",
            callback_data="translate"
        ),
        types.InlineKeyboardButton(
            text="Manage Vocabulary",
            callback_data="manage_vocabulary"
        )
    )

    await message.answer(
        f"""Hello {message.from_user.first_name}, I'm a Translator bot.\n\nI will help you with the translation in this chat or in any other group.""",
        reply_markup=builder.as_markup()
    )


# Vocabulary management menu



# Этот обработчик будет реагировать и на команду /managevoc, и на callback

@dp.message(Command("managevoc"))
@dp.callback_query(F.data == "manage_vocabulary")
async def handle_vocabulary_management(update: Message | CallbackQuery):
    # Определяем откуда пришёл запрос (сообщение или callback)
    if isinstance(update, CallbackQuery):
        message = update.message
    else:
        message = update

    builder = InlineKeyboardBuilder()
    builder.add(
        types.InlineKeyboardButton(
            text="Add Translation",
            callback_data="add_translation"
        ),
        types.InlineKeyboardButton(
            text="View Translations",
            callback_data="view_translations"
        ),
        types.InlineKeyboardButton(
            text="Clear vocabulary",
            callback_data="Clear_volabulary"
        )
    )
    builder.adjust(2, 1)

    # Для нового сообщения используем answer, для редактирования - edit_text
    if isinstance(update, CallbackQuery):
        await message.edit_text(
            """What would you like to do with the vocabulary? \n---Tip: add their language next to the words,
it can help if you keep words from different
languages in your dictionary.\n\nex. <<hello (en) - привет (ru)>>""",
            reply_markup=builder.as_markup()
        )
    else:
        await message.answer(
            """What would you like to do with the vocabulary? \n---Tip: add their language next to the words,
it can help if you keep words from different
languages in your dictionary.\n\nex. <<hello (en) - привет (ru)>>""",
            reply_markup=builder.as_markup()
        )


# Add translation flow
@dp.callback_query(F.data == "add_translation")
async def request_word(callback: CallbackQuery, state: FSMContext):
    await state.set_state(UserState.adding_word)
    await callback.message.answer("Please send me the word you want to translate:")


@dp.message(UserState.adding_word)
async def process_word(message: Message, state: FSMContext):
    await state.update_data(word=message.text)
    await state.set_state(UserState.adding_translation)
    await message.answer("Now please send me the translation:")


@dp.message(UserState.adding_translation)
async def save_translation(message: Message, state: FSMContext):
    data = await state.get_data()
    word = data['word']
    translation = message.text

    try:
        cursor.execute('INSERT INTO vocabulary (word, translation) VALUES (?, ?)', (word, translation))
        conn.commit()
        await message.answer("Translation added successfully!")
    except sqlite3.IntegrityError:
        await message.answer("This word is already in the database.")

    await state.clear()


# View translations
@dp.callback_query(F.data == "view_translations")
async def view_translations(callback: CallbackQuery):
    cursor.execute('SELECT word, translation FROM vocabulary')
    translations = cursor.fetchall()

    if translations:
        response = "Your vocabulary database:\n<<word - translation>> \n\n" + "\n".join(
            [f"{word} - {translation}" for word, translation in translations])
    else:
        response = "No translations available."

    await callback.message.answer(response)


# Clear vocabulary
@dp.callback_query(F.data == "Clear_volabulary")
async def clear_voc(callback: CallbackQuery):
    builder = InlineKeyboardBuilder()
    builder.add(
        types.InlineKeyboardButton(

            text="Clear for sure",
            callback_data="Clear_volabulary.sure" )
    )
    builder.adjust(2, 1)

    await callback.message.answer("Are you sure?")
    await asyncio.sleep(2)
    await callback.message.answer("There is the button to clear your vocabulary", reply_markup=builder.as_markup())

@dp.callback_query(F.data == "Clear_volabulary.sure")
async def clear_vocabulary(callback: CallbackQuery):
    cursor.execute('DELETE FROM vocabulary')
    conn.commit()
    await callback.message.answer("Vocabulary was cleared successfully!")


# Translation menu
@dp.callback_query(F.data == "translate")
async def welcome_callback(callback: CallbackQuery):
    builder = InlineKeyboardBuilder()
    builder.add(
        types.InlineKeyboardButton(
            text="Yes",
            callback_data="order_approve.yes"
        ),
        types.InlineKeyboardButton(
            text="Another",
            callback_data="order_approve.another"
        ),
        types.InlineKeyboardButton(
            text="Help",
            callback_data="order_approve.help"
        )
    )

    await callback.message.answer(
        f"""Firstly, if you have some problems while using bot or you want to join bot to some other chat or group please select "Help" button.
        \n\nOr if you'd prefer to use it here please follow instructions below 
        \nIs your language - '{callback.from_user.language_code}'? 
        \n(If you haven't selected language code in your profile, please select one)""",
        reply_markup=builder.as_markup()
    )


# Language selection
@dp.callback_query(F.data.startswith("order_approve."))
async def callback_handler(callback: CallbackQuery):
    action = callback.data.split('.')[1]

    if action == "another":
        await callback.message.answer('Please make sure that you have chosen the language code in your profile.')
    elif action == "yes":
        builder = InlineKeyboardBuilder()
        builder.add(
            types.InlineKeyboardButton(text="English (en)", callback_data="en"),
            types.InlineKeyboardButton(text="French (fr)", callback_data="fr"),
            types.InlineKeyboardButton(text="Belarusian (be)", callback_data="be"),
            types.InlineKeyboardButton(text="German (de)", callback_data="de")
        )
        builder.adjust(2, 2)

        await callback.message.answer(
            'An interface for manual language selection will now be displayed',
            reply_markup=builder.as_markup()
        )
    elif action == "help":
        builder = InlineKeyboardBuilder()
        builder.add(
            types.InlineKeyboardButton(
                text="Complain",
                url='https://forms.gle/9M6cbKVWPZMPYatx5'
            ),
            types.InlineKeyboardButton(
                text="← Back",
                callback_data="translate"
            )
        )

        await callback.message.answer(
            """Help reference: \n\nIf you need to add a bot to a group, then the owner of the group should add it to the desired group,
             and then give it admin rights.\n\nIf you want to complain about the translation, then go to the Google form by clicking "Complain" below.""",
            reply_markup=builder.as_markup()
        )


# Language selection handler
@dp.callback_query(F.data.in_(['en', 'fr', 'be', 'de']))
async def language_selection(callback: CallbackQuery):
    user_data[callback.message.chat.id] = {
        'state': 'translating',
        'language': callback.data
    }
    await callback.message.answer(
        f'You have selected <b>{callback.from_user.language_code} -> {callback.data}</b>. Now you can start sending messages to translate them!\n\n'
        f'<code>Type "Stop" to end the translation mode.</code>\n\n<i>(Please remember that translations are depending on your gramacy)</i>', parse_mode="HTML")


# Translation handler
@dp.message(F.text.lower() == "stop")
async def stop_translation(message: Message):
    if message.chat.id in user_data and user_data[message.chat.id]['state'] == 'translating':
        user_data[message.chat.id]['state'] = 'not_translating'
        await message.answer("Translation mode stopped.")




@dp.message()
async def translate_message(message: Message):
    if message.chat.id not in user_data or user_data[message.chat.id]['state'] != 'translating':
        return

    try:
        src = detect(message.text)
        dest = user_data[message.chat.id]['language']
        translated_text = translator.translate(message.text, src=src, dest=dest).text
        await message.reply(translated_text)
    except Exception as e:
        await message.reply(f'An error occurred: {e}')


# Database cleanup on shutdown
async def on_shutdown():
    conn.close()


# Main function
async def main():
    dp.shutdown.register(on_shutdown)
    await dp.start_polling(bot)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())