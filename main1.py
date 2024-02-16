import telebot
from telebot import types
import random
import functions
import sqlite3
import logging
# Загрузка токена из переменных окружения
bot = telebot.TeleBot(functions.poke_bot_api)

found_pokemon = []

helpinfo = """
<b>Помощь по использованию бота:</b>

/start - Начать поиск покемона
/help - Вывести это сообщение справки
/pokedex - Показать Покемонов

<b>Дополнительные команды:</b>
/help - Вывести это сообщение справки

<b>Обратите внимание:</b>
- После каждой успешной или неудачной попытки поиска вам будут предоставлены соответствующие опции.
go - Попробовать поймать покемона
keepgoing - Продолжить поиски
skip - Пропустить и попробовать еще раз
retry - Повторить попытку
- Удачи в поисках покемонов!
"""

class PokemonBot:


    def __init__(self):
        # Словарь для хранения состояний пользователей
        self.states = {}
        # Создаем таблицу для спойманных покемонов
        functions.create_captured_pokemons_table()
        functions.create_number_of_pokemons()
        functions.update_number_of_pokemons_table()

    def capture_pokemon(self, user_id, found_pokemon):
        conn = sqlite3.connect('pokedex.sql')
        cur = conn.cursor()
        # Проверяем количество pokebol у пользователя
        cur.execute(f'SELECT pokebol FROM number_of_pokebols WHERE user_id = {user_id}')
        pokebol_count = cur.fetchone()[0]
    
        if pokebol_count > 0:
            found_pokemon = found_pokemon.lower()
            # Выполняем логику захвата
            cur.execute("INSERT INTO captured_pokemons (user_id, found_pokemon) VALUES (?, ?)", (user_id, found_pokemon))
            cur.execute(f"UPDATE number_of_pokemons SET {found_pokemon} = {found_pokemon} + 1, pokebol = pokebol - 1 WHERE user_id = {user_id}")
            conn.commit()
            success = True
        else:
            success = False
    
        conn.close()
        return success
    

    def start(self, message):
        
        functions.create_users_table()
        functions.add_user_to_number_of_pokemons(message.chat.id) #добавляет только новых юзеров
        # Приветственное сообщение при старте
        bot.send_message(message.chat.id, f"Hi, {message.from_user.first_name}!\nWelcome to Poké-Hunter. This bot allows you to search and catch Pokémons.\nOpen menu and press 'Go' to start your adventure.\nPress 'help' for more information.")
    

    def handle_go_callback(self, call):
        chat_id = call.message.chat.id
        user_id = call.message.chat.id  # Для простоты предполагаем, что user_id и chat_id идентичны

        # Обработка нажатия кнопок "Go", "Keep going", "Skip"
        if call.data in ['go', 'keepgoing', 'skip']:
            found_pokemon.clear()
            if call.data in ['keepgoing', 'skip']:
                bot.delete_message(call.message.chat.id, call.message.message_id)
            if random.choice([True, False]):
                # Проверяем, есть ли у пользователя pokebol
                conn = sqlite3.connect('pokedex.sql')
                cur = conn.cursor()
                cur.execute(f'SELECT pokebol FROM number_of_pokemons WHERE user_id = {user_id}')
                pokebol_count = cur.fetchone()[0]
                conn.close()
                if pokebol_count > 0:
                    self.states[chat_id] = 'choose_catch_or_skip'
                    self.show_catch_or_skip_buttons(chat_id, call.message.message_id)
                else:
                    bot.send_message(chat_id, "У вас нет pokebol! Найдите или купите их, чтобы продолжить ловлю покемонов.")
            else:
                self.states[chat_id] = 'choose_find_or_skip'
                self.back_to_start(chat_id, call.message.message_id)


        # Обработка нажатия кнопки "Captured"
        elif call.data == 'captured':
            bot.send_message(chat_id, "Вы успешно поймали покемона!")
            self.capture_pokemon(call.message.chat.id, f"{found_pokemon[0]}")
        elif call.data == 'pokedex':
            self.show_pokedex(chat_id, call.message.message_id)
            


    def show_go_buttons(self, chat_id):
        # Отправка кнопки "Go" для начала поиска покемона
        markup = types.InlineKeyboardMarkup()

        button_go = types.InlineKeyboardButton('Go', callback_data='go')
        markup.add(button_go)

        bot.send_message(chat_id, "Press 'Go' to start searching for a Pokemon:", reply_markup=markup)

    def back_to_start(self, chat_id, message_id):
        # Возвращение к начальному состоянию после неудачной попытки
        markup = types.InlineKeyboardMarkup()
        button_back = types.InlineKeyboardButton('Keep going', callback_data='keepgoing')
        markup.add(button_back)
        bot.send_message(chat_id, 'You did not find anything', reply_markup=markup)
        #bot.delete_message(chat_id, message_id)


    def show_pokedex(self, chat_id):
        pokedex = functions.show_pokedex(chat_id)
        # Проверка на пустую строку 'pokedex' перед отправкой
        if pokedex.strip() == '':
            bot.send_message(chat_id, "No Pokemons have been captured yet.")
        else:
            bot.send_message(chat_id, pokedex)



    def show_catch_or_skip_buttons(self, chat_id, message_id):
        # Отображение кнопок "Try to Catch" и "Skip" после успешной попытки
        markup = types.InlineKeyboardMarkup()
        button_catch = types.InlineKeyboardButton('Try to Catch', callback_data='catch')
        button_skip = types.InlineKeyboardButton('Skip', callback_data='skip')
        markup.add(button_catch, button_skip)

        # Отображение случайного покемона с весами
        chosen_pokemon = functions.pokemon_catch() #функция с вероятностями выпадения покемонов в файле functions.py
        pokemon_image = f'image/{chosen_pokemon.lower()}.png'
        with open(pokemon_image, 'rb') as pokemon_photo:
            found_pokemon.append(chosen_pokemon)
            sent_message = bot.send_photo(chat_id, pokemon_photo, caption=f"You found a {chosen_pokemon}! What would you like to do?", reply_markup=markup)
            self.states[chat_id] = {'message_id': sent_message.message_id, 'state': 'choose_catch_or_skip'}
            
            

    def show_captured_or_retry_buttons(self, chat_id, message_id):
        # Отображение кнопки "Keep going" после успешного захвата
        markup = types.InlineKeyboardMarkup()
        button_go = types.InlineKeyboardButton('Keep going', callback_data='go')
        markup.add(button_go)
        self.capture_pokemon(chat_id, f"{found_pokemon[0]}")
        bot.send_message(chat_id, f"You captured a {found_pokemon[0]}!", reply_markup=markup)
        
        #bot.delete_message(chat_id, message_id)

    def show_captured_or_not_buttons(self, chat_id, message_id):
        # Отображение кнопки "Try again" после неудачной попытки захвата
        markup = types.InlineKeyboardMarkup()
        button_try_again = types.InlineKeyboardButton('Try again', callback_data='retry')
        markup.add(button_try_again)
        bot.send_message(chat_id, 'Bad luck', reply_markup=markup)
        #bot.delete_message(chat_id, message_id)

    def run(self):
        # Запуск бота в режиме бесконечного опроса
        bot.infinity_polling()

# Если файл запущен напрямую (а не импортирован как модуль)
if __name__ == "__main__":
    # Создание экземпляра класса PokemonBot
    pokemon_bot = PokemonBot()

    # Обработчики сообщений и колбеков
    @bot.message_handler(commands=['start'])
    def start_wrapper(message):
        pokemon_bot.start(message)

    @bot.message_handler(commands=['pokedex'])
    def deploy_pokedex(message):
        chat_id = message.chat.id
        pokemon_bot.show_pokedex(chat_id)

    @bot.message_handler(commands=['go'])
    def deploy_pokedex(message):
        chat_id = message.chat.id
        pokemon_bot.show_go_buttons(chat_id)

    @bot.message_handler(commands=['help'])
    def help_command(message):
            bot.send_message(message.chat.id, helpinfo, parse_mode='html')
        
    @bot.callback_query_handler(func=lambda call: call.data in ['go', 'keepgoing', 'skip', 'retry', 'catch'])
    def handle_go_callback_wrapper(call):
        markup = types.InlineKeyboardMarkup()
        bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=markup)
        pokemon_bot.handle_go_callback(call)
        

    @bot.callback_query_handler(func=lambda call: True)
    def callback_handler_wrapper(call):
        markup = types.InlineKeyboardMarkup()
        bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=markup)
        pokemon_bot.callback_handler(call)

    # Запуск бота
    pokemon_bot.run()